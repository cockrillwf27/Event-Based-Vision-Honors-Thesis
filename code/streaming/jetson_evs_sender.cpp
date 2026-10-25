// Jetson-side capture for Triton2 EVS (TRT009S-E)
// Connects, optionally sets CD Frame / ERC if the nodes exist, streams frames over TCP.
//
// Build:
//   g++ -std=c++14 -o jetson_evs_sender jetson_evs_sender.cpp \
//       -I./include/Arena -I./include/Save -I./include/GenTL \
//       -I./GenICam/library/CPP/include \
//       -L./lib -L./GenICam/library/lib/Linux64_ARM \
//       -larena -lGCBase_gcc54_v3_3_LUCID -lGenApi_gcc54_v3_3_LUCID \
//       -lLog_gcc54_v3_3_LUCID -llog4cpp_gcc54_v3_3_LUCID -lpthread
//
// Usage:
//   ./jetson_evs_sender <laptop_ip> [port=5000]

#include <iostream>
#include <string>
#include <cstring>
#include <cstdint>
#include <vector>
#include <chrono>

#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>

#include "ArenaApi.h"

void printException(const GenICam::GenericException& ge)
{
    std::cout << "GenICam exception: " << ge.what() << "\n";
}

// Try to set a node; ignore if it doesn't exist on this SDK/camera
template<typename T>
bool trySetNode(Arena::IDevice* pDevice, const char* name, T value)
{
    try {
        Arena::SetNodeValue<T>(pDevice->GetNodeMap(), name, value);
        std::cout << "  Set " << name << " = " << value << "\n";
        return true;
    }
    catch (GenICam::GenericException&) {
        std::cout << "  (skipped) node not present: " << name << "\n";
        return false;
    }
}

int main(int argc, char* argv[])
{
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <laptop_ip> [port=5000]\n";
        return 1;
    }

    std::string laptopIp = argv[1];
    int port = (argc >= 3) ? std::stoi(argv[2]) : 5000;

    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) { perror("socket"); return 1; }

    sockaddr_in servAddr{};
    servAddr.sin_family = AF_INET;
    servAddr.sin_port = htons(port);
    inet_pton(AF_INET, laptopIp.c_str(), &servAddr.sin_addr);

    std::cout << "Connecting to laptop " << laptopIp << ":" << port << "...\n";
    if (connect(sock, (sockaddr*)&servAddr, sizeof(servAddr)) < 0) {
        perror("connect");
        close(sock);
        return 1;
    }
    std::cout << "Connected.\n";

    bool exceptionThrown = false;
    try {
        Arena::ISystem* pSystem = Arena::OpenSystem();
        pSystem->UpdateDevices(100);

        std::vector<Arena::DeviceInfo> deviceInfos = pSystem->GetDevices();
        if (deviceInfos.empty()) {
            std::cout << "No camera found.\n";
            Arena::CloseSystem(pSystem);
            close(sock);
            return 1;
        }

        Arena::IDevice* pDevice = pSystem->CreateDevice(deviceInfos[0]);
        std::cout << "Connected to: " << deviceInfos[0].ModelName()
                  << "  S/N " << deviceInfos[0].SerialNumber()
                  << "  IP " << deviceInfos[0].IpAddressStr() << "\n";

        // Try EVS-related nodes (may not exist on ARM64 SDK)
        trySetNode<GenICam::gcstring>(pDevice, "EVSOutputFrame", "CDFrame");
        trySetNode<bool>(pDevice, "EventRateControlEnable", true);
        trySetNode<double>(pDevice, "EventRateControlMaxRate", 40.0);

        std::cout << "Starting stream...\n";
        pDevice->StartStream();

        const int NUM_FRAMES = 300;
        for (int i = 0; i < NUM_FRAMES; ++i) {
            Arena::IImage* pImage = pDevice->GetImage(2000);
            if (pImage->IsIncomplete()) {
                std::cout << "Incomplete frame " << i << "\n";
                pDevice->RequeueBuffer(pImage);
                continue;
            }

            size_t dataSize = pImage->GetSizeFilled();
            const uint8_t* pData = pImage->GetData();

            uint32_t len = htonl(static_cast<uint32_t>(dataSize));
            if (send(sock, &len, sizeof(len), 0) != sizeof(len)) {
                std::cerr << "Send length failed\n";
                break;
            }
            size_t sent = 0;
            while (sent < dataSize) {
                ssize_t n = send(sock, pData + sent, dataSize - sent, 0);
                if (n <= 0) break;
                sent += n;
            }

            std::cout << "Sent frame " << i << " (" << dataSize << " bytes)\n";
            pDevice->RequeueBuffer(pImage);
        }

        pDevice->StopStream();
        pSystem->DestroyDevice(pDevice);
        Arena::CloseSystem(pSystem);
    }
    catch (GenICam::GenericException& ge) {
        printException(ge);
        exceptionThrown = true;
    }

    close(sock);
    std::cout << "Done.\n";
    return exceptionThrown ? -1 : 0;
}
