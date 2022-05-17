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
    <section>
      <div class="row">
        <div
          v-for="(value, label) in simpleCapabilities"
          :key="label"
          class="col-md-3"
        >
          <strong>{{ label }}: </strong>{{ value }}
        </div>
      </div>
      <div
        v-for="(group, groupLabel) in advancedCapabilities"
        :key="groupLabel"
        class="row"
      >
        <div class="col-md-12">
          <h5 class="bg-success">{{ groupLabel }}</h5>
        </div>
        <div v-for="(value, label) in group" :key="label" class="col-md-3">
          <strong>{{ label }}: </strong>{{ value }}
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hardware-details {
  margin: 1rem 0;
  padding: 1rem 0;
}

.node-type {
  margin-left: 1em;
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
    return {
      simpleCapabilities: mapValues(simpleCapabilities, ({ capability }) =>
        this.resolveCapability(capability)
      ),
      advancedCapabilities: mapValues(
        advancedCapabilities,
        ({ discover, custom }) => {
          let allCapabilities = {};

          if (discover) {
            allCapabilities = {
              ...allCapabilities,
              ...mapKeys(
                JSPath.apply(discover.prefix, this.hardware)[0] || {},
                capitalCase
              ),
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
        }
      ),
    };
  },
  methods: {
    resolveCapability(capability) {
      if (typeof capability === "function") {
        return capability(this.hardware);
      } else {
        return JSPath.apply(capability, this.hardware)[0];
      }
    },
  },
};
</script>
