<template>
  <div>
    <p class="lead">
      Filter nodes using the options below, then generate a reservation script
      to reserve those nodes.
    </p>
    <h4>
      Applied Filters:
      <span v-if="!activeFilters.length"> None</span>
      <span
        v-for="filter in activeFilters"
        :key="filter.label"
        class="label label-default label-filter"
      >
        <span class="label-text"
          >{{ filter.label }}
          <span
            v-on:click="toggleFilter(filter)"
            class="pseudolink fa fa-times"
          ></span>
        </span>
      </span>
    </h4>
    <h4 class="filter-state">
      <strong>{{ total }} node<span v-if="total > 1">s</span></strong>
      <span v-if="total < maximum">
        filtered from {{ maximum }} originally.
      </span>
    </h4>
    <div class="row">
      <div v-for="filter in filters" :key="filter.label" class="col col-sm-3">
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

    <input
      type="text"
      name="nodeViewSearch"
      v-on:input="updateSearch()"
      placeholder="Search by any node properties."
    />
    <toggle-button
      v-model="searchStrict"
      :labels="{ checked: 'ALL', unchecked: 'ANY' }"
    ></toggle-button>
    <button class="btn btn-sm" v-on:click="clearSearch()">Clear</button>
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
import ToggleButton from "vue-js-toggle-button";
import Vue from "vue";

Vue.use(ToggleButton);

function createFilter(label, filterFn) {
  return { label, filterFn, active: false, maxMatches: 0, currentMatches: 0 };
}

export default {
  props: {
    filteredNodes: Array,
    allNodes: Array,
  },
  data() {
    return {
      filters: [
        createFilter(
          "Cascade Lake",
          ({ nodeType }) => nodeType.indexOf("compute_cascadelake") === 0
        ),
        createFilter(
          "Skylake",
          ({ nodeType }) => nodeType === "compute_skylake"
        ),
        createFilter("GPU", ({ nodeType }) => nodeType.indexOf("gpu_") === 0),
        createFilter(
          "Storage Hierarchy",
          ({ nodeType }) => nodeType === "storage_hierarchy"
        ),
        createFilter("FPGA", ({ nodeType }) => nodeType === "fpga"),
      ],
    };
  },
  watch: {
    filteredNodes: function () {
      this.updateFilterCounts();
    },
  },
  computed: {
    activeFilters() {
      return this.filters.filter(({ active }) => active);
    },
    maximum() {
      return this.allNodes.length;
    },
    total() {
      return this.filteredNodes.length;
    },
  },
  methods: {
    toggleFilter(filter) {
      filter.active = !filter.active;
      this.$emit(
        "filtersChange",
        this.activeFilters.map(({ filterFn }) => filterFn)
      );
    },
    updateFilterCounts() {
      for (const filter of this.filters) {
        filter.currentMatches = 0;
      }
      for (const node of this.filteredNodes) {
        for (const filter of this.filters) {
          if (filter.filterFn(node)) {
            filter.currentMatches++;
          }
        }
      }
    },
  },
  mounted() {
    for (const node of this.allNodes) {
      for (const filter of this.filters) {
        if (filter.filterFn(node)) {
          filter.maxMatches++;
        }
      }
    }
    this.updateFilterCounts();
  },
};
</script>
