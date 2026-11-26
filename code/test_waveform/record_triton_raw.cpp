// record_triton_raw.cpp
// Acquisition thread: GetImage → copy → RequeueBuffer → push to queue
// Writer thread: drain queue to disk
// Build (adjust SDK paths):
// g++ -std=c++17 -O2 -o record_triton_raw record_triton_raw.cpp \
//   -I/home/orin/Downloads/ArenaSDK_Linux_ARM64/include/Arena \
//   -I/home/orin/Downloads/ArenaSDK_Linux_ARM64/include/Save \
//   -I/home/orin/Downloads/ArenaSDK_Linux_ARM64/include/GenTL \
//   -I/home/orin/Downloads/ArenaSDK_Linux_ARM64/GenICam/library/CPP/include \
//   -L/home/orin/Downloads/ArenaSDK_Linux_ARM64/lib \
//   -L/home/orin/Downloads/ArenaSDK_Linux_ARM64/GenICam/library/lib/Linux64_ARM \
//   -larena -lGCBase_gcc54_v3_3_LUCID -lGenApi_gcc54_v3_3_LUCID \
//   -lLog_gcc54_v3_3_LUCID -llog4cpp_gcc54_v3_3_LUCID -lpthread

#include "ArenaApi.h"
#include <iostream>
#include <fstream>
#include <chrono>
#include <string>
#include <vector>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <thread>
#include <atomic>
#include <unistd.h>

struct Frame {
    std::vector<uint8_t> data;
    uint64_t host_ts_us = 0;
};

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <output.raw> [duration_sec]\n";
        return 1;
    }
    std::string outPath = argv[1];
    double duration = (argc >= 3) ? std::stod(argv[2]) : 30.0;

    const size_t QUEUE_MAX = 256;          // frames held in RAM
    const int    SDK_BUFFERS = 50;         // StartStream(N)
    const double ERC_MEV = 40.0;           // safe for 1 GigE

    Arena::ISystem* pSystem = nullptr;
    Arena::IDevice* pDevice = nullptr;

    try {
        pSystem = Arena::OpenSystem();
        pSystem->UpdateDevices(100);
        auto deviceInfos = pSystem->GetDevices();
        if (deviceInfos.empty()) {
            std::cerr << "No camera found\n";
            Arena::CloseSystem(pSystem);
            return 1;
        }
        pDevice = pSystem->CreateDevice(deviceInfos[0]);
        std::cout << "Opened " << deviceInfos[0].ModelName()
                  << "  SN " << deviceInfos[0].SerialNumber() << "\n";

        // Safer ERC for 1 GigE (ignore if node missing)
        try {
            Arena::SetNodeValue<bool>(pDevice->GetNodeMap(), "EventRateControlEnable", true);
            Arena::SetNodeValue<double>(pDevice->GetNodeMap(), "EventRateControlMaxRate", ERC_MEV);
            std::cout << "ERC set to " << ERC_MEV << " Mev/s\n";
        } catch (...) {
            std::cout << "ERC nodes not available (continuing)\n";
        }

        // Optional: force raw EVT 3.0 if the node exists
        try {
            Arena::SetNodeValue<GenICam::gcstring>(pDevice->GetNodeMap(),
                                                   "EVSOutputFrame", "EVT3");
            std::cout << "EVSOutputFrame = EVT3\n";
        } catch (...) {}

        pDevice->StartStream(SDK_BUFFERS);
        std::cout << "Started stream with " << SDK_BUFFERS << " buffers\n";

        std::ofstream out(outPath, std::ios::binary);
        if (!out) {
            std::cerr << "Cannot open " << outPath << "\n";
            pDevice->StopStream();
            pSystem->DestroyDevice(pDevice);
            Arena::CloseSystem(pSystem);
            return 1;
        }

        std::queue<Frame> q;
        std::mutex q_mtx;
        std::condition_variable q_cv;
        std::atomic<bool> running{true};
        std::atomic<uint64_t> frames_written{0};
        std::atomic<uint64_t> bytes_written{0};

        // Writer thread
        std::thread writer([&]() {
            while (running.load() || !q.empty()) {
                Frame f;
                {
                    std::unique_lock<std::mutex> lk(q_mtx);
                    q_cv.wait(lk, [&]{ return !q.empty() || !running.load(); });
                    if (q.empty()) continue;
                    f = std::move(q.front());
                    q.pop();
                }
                if (!f.data.empty()) {
                    out.write(reinterpret_cast<const char*>(f.data.data()), f.data.size());
                    frames_written++;
                    bytes_written += f.data.size();
                    if (frames_written % 200 == 0) out.flush();
                }
            }
            out.flush();
        });

        auto t0 = std::chrono::steady_clock::now();
        uint64_t frames_in = 0;
        std::cout << "Recording to " << outPath << " for " << duration << " s...\n";

        while (true) {
            auto elapsed = std::chrono::duration<double>(
                std::chrono::steady_clock::now() - t0).count();
            if (elapsed >= duration) break;

            Arena::IImage* pImage = pDevice->GetImage(500);
            if (!pImage) continue;

            if (pImage->IsIncomplete()) {
                pDevice->RequeueBuffer(pImage);
                continue;
            }

            size_t sz = pImage->GetSizeFilled();
            const uint8_t* data = pImage->GetData();
            if (data && sz > 0 && sz < 8*1024*1024) {
                Frame f;
                f.data.assign(data, data + sz);          // copy first
                f.host_ts_us = std::chrono::duration_cast<std::chrono::microseconds>(
                    std::chrono::steady_clock::now() - t0).count();

                pDevice->RequeueBuffer(pImage);          // release immediately

                // push to queue (drop oldest if full — better than stalling acquisition)
                {
                    std::unique_lock<std::mutex> lk(q_mtx);
                    if (q.size() >= QUEUE_MAX) q.pop();  // simple drop-oldest
                    q.push(std::move(f));
                }
                q_cv.notify_one();
                frames_in++;
            } else {
                pDevice->RequeueBuffer(pImage);
            }

            if (frames_in % 1000 == 0 && frames_in > 0) {
                std::cout << "  " << elapsed << " s  frames=" << frames_in
                          << "  written=" << frames_written
                          << "  MB=" << (bytes_written/1e6) << "\n";
            }
        }

        running = false;
        q_cv.notify_all();
        writer.join();

        std::cout << "Done. Frames in=" << frames_in
                  << "  written=" << frames_written
                  << "  bytes=" << bytes_written << "\n";

        pDevice->StopStream();
        pSystem->DestroyDevice(pDevice);
        Arena::CloseSystem(pSystem);
        return 0;

    } catch (GenICam::GenericException& e) {
        std::cerr << "Arena exception: " << e.what() << "\n";
        if (pDevice) {
            try { pDevice->StopStream(); } catch (...) {}
            try { pSystem->DestroyDevice(pDevice); } catch (...) {}
        }
        if (pSystem) try { Arena::CloseSystem(pSystem); } catch (...) {}
        return 1;
    } catch (std::exception& e) {
        std::cerr << "std exception: " << e.what() << "\n";
        return 1;
    }
}
