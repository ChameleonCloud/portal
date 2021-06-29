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
    tagPrefix: "Threads: "
  },
  "RAM Size": {
    capability: ".mainMemory.humanizedRamSize",
    tagPrefix: "RAM: "
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
    tagPrefix: "Storage: "
  }
};

export const advancedCapabilities = {
  Processor: { discover: { prefix: ".processor" } },
  Placement: { discover: { prefix: ".placement", ignore: ["node"] } },
  FPGA: { discover: { prefix: ".fpga" } },
  "Network Devices": {
    custom: {
      "# Active Devices": {
        capability({ networkAdapters }) {
          return networkAdapters.filter(({ enabled }) => enabled).length;
        },
        tagPrefix: "Networks: ",
      }
    }
  },
  "Storage Devices": {
    custom: {
      SSD: {
        capability({ storageDevices }) {
          return storageDevices.some(({ model }) =>
            model.toLowerCase().includes("ssd")
          )
            ? "Yes"
            : "No";
        },
        tagPrefix: "SSD: ",
      },
      NVMe: {
        capability({ storageDevices }) {
          return storageDevices.some(({ driver }) => driver === "nvme")
            ? "Yes"
            : "No";
        },
        tagPrefix: "NVMe: ",
      },
    },
  }
};