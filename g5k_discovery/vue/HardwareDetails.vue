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
</style>

<script>
import JSPath from "jspath";
import { advancedCapabilities, simpleCapabilities } from "./capabilities";
import { mapValues } from "./utils";

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
          if (discover) {
            return JSPath.apply(discover.prefix, this.hardware)[0];
          } else {
            return mapValues(custom, ({ capability }) =>
              this.resolveCapability(capability)
            );
          }
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
