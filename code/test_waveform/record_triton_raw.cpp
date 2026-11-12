#include "ArenaApi.h"
#include <iostream>
#include <fstream>
#include <chrono>
#include <string>
#include <unistd.h>

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <output.raw> [duration_sec]\n";
        return 1;
    }
    std::string outPath = argv[1];
    double duration = (argc >= 3) ? std::stod(argv[2]) : 30.0;

    Arena::ISystem* pSystem = Arena::OpenSystem();
    pSystem->UpdateDevices(100);
    auto deviceInfos = pSystem->GetDevices();
    if (deviceInfos.empty()) {
        std::cerr << "No camera found\n";
        Arena::CloseSystem(pSystem);
        return 1;
    }
    Arena::IDevice* pDevice = pSystem->CreateDevice(deviceInfos[0]);
    std::cout << "Opened " << deviceInfos[0].ModelName() << "\n";

    // Optional: try to set event mode (ignore errors if node missing)
    try { Arena::SetNodeValue<bool>(pDevice->GetNodeMap(), "EventRateControlEnable", true); } catch (...) {}
    try { Arena::SetNodeValue<double>(pDevice->GetNodeMap(), "EventRateControlMaxRate", 100.0); } catch (...) {}

    pDevice->StartStream();
    std::ofstream out(outPath, std::ios::binary);
    if (!out) {
        std::cerr << "Cannot open " << outPath << "\n";
        pDevice->StopStream();
        pSystem->DestroyDevice(pDevice);
        Arena::CloseSystem(pSystem);
        return 1;
    }

    auto t0 = std::chrono::steady_clock::now();
    int frames = 0;
    const int MAX_FRAMES = 200000;  // hard safety limit
    std::cout << "Recording to " << outPath << " for " << duration << " s...\n";

    while (frames < MAX_FRAMES) {
        auto elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
        if (elapsed >= duration) break;

        Arena::IImage* pImage = pDevice->GetImage(200);
        if (!pImage || pImage->IsIncomplete()) {
            if (pImage) pDevice->RequeueBuffer(pImage);
            usleep(1000);  // 1 ms pause
            continue;
        }

        size_t sz = pImage->GetSizeFilled();
        const uint8_t* data = pImage->GetData();
        if (data && sz > 0 && sz < 10*1024*1024) {  // sanity size check
            out.write(reinterpret_cast<const char*>(data), sz);
            frames++;
        }
        pDevice->RequeueBuffer(pImage);

        if (frames % 500 == 0) {
            out.flush();
            usleep(500);
        }
    }
    return 0;
}
