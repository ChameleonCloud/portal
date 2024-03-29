// Copyright 2021 University of Chicago
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

const GPUDIRECT_MODELS = ["v100", "p100", "m40", "k80", "rtx 6000"];
const GB_FACTOR = 1024 * 1024 * 1024;
const storageSizeBuckets = {
  "< 200GB": [0, 200 * GB_FACTOR],
  "200-400GB": [200 * GB_FACTOR, 400 * GB_FACTOR],
  "400GB-1TB": [400 * GB_FACTOR, 1000 * GB_FACTOR],
  ">1TB": [1000 * GB_FACTOR, Number.POSITIVE_INFINITY],
};

export const simpleCapabilities = {
  Site: { capability: ".parent.parent.uid" },
  "Platform Type": {
    capability: ".architecture.platformType",
  },
  "# CPUS": {
    capability: ".architecture.smpSize",
    tagPrefix: "CPUS: ",
  },
  "# Threads": {
    capability: ".architecture.smtSize",
    tagPrefix: "Threads: ",
  },
  "RAM Size": {
    capability: ".mainMemory.humanizedRamSize",
    tagPrefix: "RAM: ",
  },
  "Total Storage": {
    capability(node) {
      const total = node.storageDevices.reduce((sum, dev) => {
        return sum + dev.size;
      }, 0);
      for (const bucket in storageSizeBuckets) {
        if (
          total >= storageSizeBuckets[bucket][0] &&
          total < storageSizeBuckets[bucket][1]
        ) {
          return bucket;
        }
      }
      return "Unknown";
    },
    tagPrefix: "Storage: ",
  },
};

export const advancedCapabilities = {
  Processor: { discover: { prefix: ".processor" } },
  Placement: { discover: { prefix: ".placement", ignore: ["node"] } },
  GPU: { discover: { prefix: ".gpu" } },
  FPGA: { discover: { prefix: ".fpga" } },
  "Network Devices": {
      custom: {
          "# Active Devices": {
                capability({networkAdapters}) {
                    return networkAdapters.filter(({enabled}) => enabled).length;
                },
                tagPrefix: "Networks: ",
            },
        },
        discover: {
            prefix: ".networkAdapters",
            ignore: ["device", "enabled", "interface", "mac", "rate", "driver",
                "management", "bridged", "mounted", "guid", "version"]
        }
    },
    "SSD": {
        custom: {
            SSD: {
                capability({storageDevices}) {
                    return storageDevices.some(
                        ({model, mediaType}) =>
                            model.toLowerCase().includes("ssd") ||
                            (mediaType || "").toLowerCase() === "ssd"
                    )
                        ? "Yes"
                        : "No";
                },
            },
        },
        discover:
            {
                prefix: ".storageDevices",
                ignore: ["device", "humanizedSize", "interface", "size", "rev",
                    "mediaType", "driver"]
            },
    },
    "NVMe": {
        custom: {
            NVMe: {
                capability({storageDevices}) {
                    return storageDevices.some(
                        ({driver, interface: iface}) =>
                            driver === "nvme" || (iface || "").toLowerCase() === "pcie"
                    )
                        ? "Yes"
                        : "No";
                },
                tagPrefix: "NVMe: ",
            },
        },
    },
  RDMA: {
    custom: {
      InfiniBand: {
        capability({ infiniband }) {
          return infiniband ? "Yes" : "No";
        },
      },
      GPUDirect: {
        capability({ infiniband, gpu }) {
          return infiniband &&
            gpu &&
            gpu.gpuModel &&
            gpu.gpuModel.toLowerCase() in GPUDIRECT_MODELS
            ? "Yes"
            : "No";
        },
      },
      NVMEoF: {
        capability({ infiniband, storageDevices }) {
          let ibPresent = infiniband;
          let nvmePresent = storageDevices.some(
            ({ driver, interface: iface }) =>
              driver === "nvme" || (iface || "").toLowerCase() === "pcie"
          );
          return ibPresent && nvmePresent ? "Yes" : "No";
        },
      },
    },
  },
};
