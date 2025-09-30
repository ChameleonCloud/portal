<template>
  <div class="hardware-details">
    <h4 class="node-header">
      <a
        :href="
          'node/sites/' +
          hardware.parent.parent.uid +
          '/clusters/' +
          hardware.parent.uid +
          '/nodes/' +
          hardware.uid
        "
        >{{ hardware.nodeName || hardware.uid }}</a
      >
      <span class="label label-default node-type">{{ hardware.nodeType }}</span>
    </h4>
    <section class="capabilities">
      <div class="simple-capabilities">
        <dl class="dl-horizontal">
          <template v-for="(value, label) in simpleCapabilities">
            <dt :key="label + '-dt'">{{ label }}</dt>
            <dd :key="label + '-dd'">{{ value }}</dd>
          </template>
        </dl>
      </div>
      <div class="advanced-capabilities">
        <template v-for="(group, groupLabel) in advancedCapabilities">
          <div
            v-if="Object.keys(group).length > 0"
            :key="groupLabel"
            class="capability-group"
          >
            <h5 @click="toggle(groupLabel)" class="capability-group-header">
              <span
                class="fa"
                :class="{
                  'fa-caret-right': collapsed[groupLabel],
                  'fa-caret-down': !collapsed[groupLabel],
                }"
              ></span>
              {{ groupLabel }}
            </h5>
            <div v-show="!collapsed[groupLabel]" class="capability-group-body">
              <dl class="dl-horizontal">
                <template v-for="(value, label) in group">
                  <dt :key="label + '-dt'">{{ label }}</dt>
                  <dd :key="label + '-dd'">{{ value }}</dd>
                </template>
              </dl>
            </div>
          </div>
        </template>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hardware-details {
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 1rem;
  margin: 1rem 0;
}

.node-type {
  margin-left: 1em;
}

.capabilities {
  margin-top: 1rem;
}

.simple-capabilities {
  font-size: 1.1em;
}

.dl-horizontal dt {
  width: 120px;
}

.dl-horizontal dd {
  margin-left: 140px;
}

.capability-group-header {
  cursor: pointer;
  font-weight: bold;
  margin-top: 1rem;
  color: #337ab7;
}

.capability-group-header .fa {
  margin-right: 0.5em;
}

.capability-group-body {
  padding-left: 1.5em;
}
</style>

<script>
import JSPath from "jspath";
import { capitalCase } from "change-case";
import { advancedCapabilities, simpleCapabilities } from "./capabilities";
import { mapKeys, mapValues } from "./utils";

export default {
  props: {
    hardware: Object,
  },
  data() {
    const advancedCapabilities = this.discoverAdvancedCapabilities();
    const preferredOrder = ["Processor", "GPU", "SSD"];
    const reorderedAdvancedCapabilities = {};

    // Add preferred keys first, in order
    for (const key of preferredOrder) {
      if (advancedCapabilities[key]) {
        reorderedAdvancedCapabilities[key] = advancedCapabilities[key];
      }
    }

    // Add remaining keys
    for (const key in advancedCapabilities) {
      if (!reorderedAdvancedCapabilities.hasOwnProperty(key)) {
        reorderedAdvancedCapabilities[key] = advancedCapabilities[key];
      }
    }

    return {
      simpleCapabilities: mapValues(simpleCapabilities, ({ capability }) =>
        this.resolveCapability(capability)
      ),
      advancedCapabilities: reorderedAdvancedCapabilities,
      collapsed: Object.keys(reorderedAdvancedCapabilities).reduce((acc, key) => {
        acc[key] = !preferredOrder.includes(key);
        return acc;
      }, {}),
    };
  },
  methods: {
    discoverAdvancedCapabilities() {
      return mapValues(advancedCapabilities, (group) =>
        this.processAdvancedGroup(group)
      );
    },
    processAdvancedGroup({ discover, custom }) {
      let allCapabilities = {};

      if (discover) {
        const discoveredCaps = JSPath.apply(discover.prefix, this.hardware)[0] || {};
        if (discover.ignore) {
          discover.ignore.forEach((key) => delete discoveredCaps[key]);
        }
        allCapabilities = {
          ...allCapabilities,
          ...mapKeys(discoveredCaps, capitalCase),
        };
      }

      if (custom) {
        allCapabilities = {
          ...allCapabilities,
          ...mapValues(custom, ({ capability }) =>
            this.resolveCapability(capability)
          ),
        };
      }

      return allCapabilities;
    },
    resolveCapability(capability) {
      if (typeof capability === "function") {
        return capability(this.hardware);
      } else {
        return JSPath.apply(capability, this.hardware)[0];
      }
    },
    toggle(groupLabel) {
      this.$set(this.collapsed, groupLabel, !this.collapsed[groupLabel]);
    },
  },
};
</script>
