<template>
  <div>
    <h4>
      Applied Filters:
      <span v-if="!activeFilters.length"> None</span>
      <span v-for="filter in activeFilters" :key="filter.label">
        <span class="label label-default">
          <span class="label-text"
            >{{ filter.tagLabel }}
            <span
              v-on:click="toggleFilter(filter)"
              class="pseudolink fa fa-times"
            ></span>
          </span> </span
        >{{ " " }}
      </span>
    </h4>

    <h4 class="filter-state">
      <strong>{{ total }} node<span v-if="total > 1">s</span></strong>
      <span v-if="total < maximum">
        filtered from {{ maximum }} originally.
      </span>
    </h4>

    <div class="row">
      <div
        v-for="filter in coarseFilters"
        :key="filter.label"
        class="col col-sm-3"
      >
        <button
          type="button"
          class="btn btn-lg btn-primary btn-filter btn-block"
          :disabled="!filter.currentMatches"
          v-on:click="toggleFilter(filter)"
        >
          <span
            class="fa fa-check-square-o"
            v-if="filter.maxMatches === total"
          ></span>
          {{ filter.label }}
          <span v-if="filter.currentMatches"
            >({{ filter.currentMatches }})</span
          >
        </button>
      </div>
    </div>

    <div class="row">
      <div
        v-for="(filters, groupLabel) in simpleCapabilityFilters"
        :key="groupLabel"
        class="col col-sm-2"
      >
        <strong>{{ groupLabel }}</strong>

        <div v-for="filter in filters" :key="filter.label" class="checkbox">
          <label
            ><input
              type="checkbox"
              :name="groupLabel"
              :value="filter.label"
              :checked="filter.active"
              :disabled="!filter.currentMatches"
              v-on:change="toggleFilter(filter)"
            />
            {{ filter.label }} ({{ filter.currentMatches }})</label
          >
        </div>
      </div>
    </div>

    <div class="row">
      <div class="col-md-12">
        <h4>
          <a role="button" v-on:click="toggleAdvancedFilters()"
            ><span
              class="fa"
              :class="{
                'fa-minus': showAdvanced,
                'fa-plus': !showAdvanced,
              }"
            ></span>
            Advanced Filters</a
          >
        </h4>
        <div v-if="showAdvanced">
          <div
            v-for="(advFilters, sectionLabel) in advancedCapabilityFilters"
            :key="sectionLabel"
            class="filter-section"
          >
            <h5 class="bg-success">{{ sectionLabel }}</h5>
            <div class="row">
              <div
                class="col-md-2"
                v-for="(filters, groupLabel) in advFilters"
                :key="groupLabel"
              >
                <strong>{{ groupLabel }}</strong>
                <div
                  v-for="filter in filters"
                  :key="filter.label"
                  class="checkbox"
                >
                  <label
                    ><input
                      type="checkbox"
                      :name="sectionLabel"
                      :value="filter.label"
                      :checked="filter.active"
                      :disabled="!filter.currentMatches"
                      v-on:change="toggleFilter(filter)"
                    />
                    {{ filter.label }} ({{ filter.currentMatches }})</label
                  >
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <h4 class="filter-state">
      <strong>{{ total }} node<span v-if="total > 1">s</span></strong>
      <span v-if="total < maximum">
        filtered from {{ maximum }} originally.
      </span>
    </h4>
  </div>
</template>

<style scoped>
.btn-filter {
  margin-bottom: 20px;
}
</style>

<script>
import JSPath from "jspath";
import { capitalCase, snakeCase } from "change-case";
import { advancedCapabilities, simpleCapabilities } from "./capabilities";

function createFilter(label, filterFn, options) {
  const constraint = options && options.constraint;

  if (typeof filterFn === "string") {
    const pathSpec = filterFn;
    filterFn = (nodes) => {
      return { result: JSPath.apply(pathSpec, nodes), constraint };
    };
  }

  const tagLabel = `${(options && options.tagPrefix) || ""}${label}`;
  return {
    label,
    tagLabel,
    filterFn,
    active: false,
    maxMatches: 0,
    currentMatches: 0,
  };
}

function sortChoices(a, b) {
  if (!isNaN(parseInt(a)) && !isNaN(parseInt(b))) {
    return parseInt(a) > parseInt(b) ? 1 : -1;
  }
  return a > b ? 1 : -1;
}

function createCapabilityFilters(capability, nodes, options) {
  const choices = new Set(JSPath.apply(capability, nodes));
  return Array.from(choices)
    .sort(sortChoices)
    .map((choice) => {
      const parts = capability.split(".");
      const suffix = parts.pop();
      const choiceMatcher = typeof choice === "string" ? `"${choice}"` : choice;

      let constraint = null;
      // Blazar can't go up the chain using the "parent" syntax we use here.
      // Treat this as not having a sane constraint;
      if (!capability.includes("parent")) {
        constraint = [
          "==",
          `\$${parts.slice(1).concat(suffix).map(snakeCase).join(".")}`,
          choice,
        ];
      }

      return createFilter(
        choice,
        `.{${parts.join(".")}.${suffix} === ${choiceMatcher}}`,
        {
          constraint,
          ...options,
        }
      );
    });
}

function createRawCapabilityFilters(capabilityFn, nodes, options) {
  const choices = new Set(nodes.map(capabilityFn));
  return Array.from(choices)
    .sort(sortChoices)
    .map((choice) => {
      return createFilter(
        choice,
        (nodes) => nodes.filter((n) => capabilityFn(n) === choice),
        options
      );
    });
}

function createAdvancedCapabilityFilters(pathSpec, nodes, options) {
  const entries = JSPath.apply(pathSpec, nodes);
  const subKeys = new Set(
    Array.prototype.concat.apply([], entries.map(Object.keys))
  );
  if (options && options.ignore) {
    options.ignore.forEach((key) => subKeys.delete(key));
  }
  const filters = {};
  subKeys.forEach((subPath) => {
    filters[capitalCase(subPath)] = createCapabilityFilters(
      `${pathSpec}.${subPath}`,
      nodes,
      { tagPrefix: `${subPath}: ` }
    );
  });
  return filters;
}

export default {
  props: {
    filteredNodes: Array,
    allNodes: Array,
  },
  data() {
    // Needs to be an arrow-function because we need 'this' reference.
    const processCapabilities = (capabilities) => {
      return Object.fromEntries(
        Object.entries(capabilities).map(([key, { capability, tagPrefix }]) => {
          const factoryFn =
            typeof capability === "function"
              ? createRawCapabilityFilters
              : createCapabilityFilters;
          return [key, factoryFn(capability, this.allNodes, { tagPrefix })];
        })
      );
    };

    const coarseFilters = createCapabilityFilters(".nodeType", this.allNodes);
    const simpleCapabilityFilters = processCapabilities(simpleCapabilities);
    const advancedCapabilityFilters = Object.fromEntries(
      Object.entries(advancedCapabilities).map(
        ([key, { discover, custom }]) => {
          const discoveredCaps = discover
            ? createAdvancedCapabilityFilters(discover.prefix, this.allNodes, {
                ignore: discover.ignore,
              })
            : {};
          const customCaps = custom ? processCapabilities(custom) : {};
          return [key, { ...discoveredCaps, ...customCaps }];
        }
      )
    );

    return {
      showAdvanced: false,
      coarseFilters,
      simpleCapabilityFilters,
      advancedCapabilityFilters,
    };
  },
  watch: {
    filteredNodes: function () {
      this.updateFilterCounts();
    },
  },
  computed: {
    allFilters() {
      let all = Array.from(this.coarseFilters);
      all = all.concat(...Object.values(this.simpleCapabilityFilters));
      for (const section in this.advancedCapabilityFilters) {
        all = all.concat(
          ...Object.values(this.advancedCapabilityFilters[section])
        );
      }
      return all;
    },
    activeFilters() {
      return this.allFilters.filter(({ active }) => active);
    },
    maximum() {
      return this.allNodes.length;
    },
    total() {
      return this.filteredNodes.length;
    },
  },
  methods: {
    reset() {
      for (const filter of this.allFilters) {
        filter.active = false;
      }
      this.$emit("filtersChange", []);
    },
    toggleFilter(filter) {
      filter.active = !filter.active;
      this.$emit(
        "filtersChange",
        this.activeFilters.map(({ filterFn }) => filterFn)
      );
    },
    toggleAdvancedFilters() {
      this.showAdvanced = !this.showAdvanced;
    },
    getFilterResult(filter, nodeList) {
      let result = filter.filterFn(nodeList);
      return Array.isArray(result) ? result : result.result;
    },
    updateFilterCounts() {
      const isFiltered = this.allNodes.length > this.filteredNodes.length;
      for (const filter of this.allFilters) {
        // Save performance on a common case, where there are no filters in play.
        if (isFiltered) {
          filter.currentMatches = this.getFilterResult(
            filter,
            this.filteredNodes
          ).length;
        } else {
          filter.currentMatches = filter.maxMatches;
        }
      }
    },
  },
  mounted() {
    for (const filter of this.allFilters) {
      filter.currentMatches = filter.maxMatches = this.getFilterResult(
        filter,
        this.allNodes
      ).length;
    }
  },
};
</script>
