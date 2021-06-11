<template>
  <div>
    <div class="row">
      <div class="col-md-12">
        <div v-if="loading">
          <div class="well">
            <h4>
              <span class="fa fa-refresh fa-spin"></span> Loading nodes...
            </h4>
          </div>
        </div>
        <div v-else>
          <div v-if="panel === 'search'">
            <HardwareCatalogueFilters
              v-bind:filteredNodes="filteredNodes"
              v-bind:allNodes="allNodes"
              v-on:filtersChange="onFiltersChanged"
            />

            <div class="btn-group">
              <button
                class="btn btn-sm btn-success"
                v-on:click="showReservationScript()"
              >
                Reserve
              </button>
              <button
                class="btn btn-sm btn-info"
                v-on:click="changeView('results')"
              >
                View
              </button>
            </div>
            <div class="btn-group">
              <button class="btn btn-sm" v-on:click="reset()">Reset</button>
            </div>
          </div>

          <ol v-if="panel === 'results'">
            <li v-for="node in filteredNodes" :key="node.uid" class="node">
              <h4 class="node-header">
                <a
                  :href="
                    'node/sites/' +
                    node.parent.parent.uid +
                    '/clusters/' +
                    node.parent.uid +
                    '/nodes/' +
                    node.uid
                  "
                  >{{ node.nodeName || node.uid }}</a
                >
              </h4>
              <section>
                <div class="row">
                  <div class="col col-sm-3">
                    <strong>Site: </strong>{{ node.parent.parent.uid }}
                  </div>
                  <div class="col col-sm-3">
                    <strong>Node Type: </strong>{{ node.nodeType }}
                  </div>
                </div>
              </section>
            </li>
          </ol>
          <div v-if="!filteredNodes" class="alert alert-warning">
            Node(s) not found.
          </div>
          <div class="btn-group">
            <button class="btn btn-sm" v-on:click="changeView('search')">
              Back
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>

<script>
import axios from "axios";
import HardwareCatalogueFilters from "./HardwareCatalogueFilters.vue";

function extractLink(links, linkRel) {
  const link = links.find(({ rel }) => rel === linkRel);
  return link ? `${link.href.replace("/", "")}.json` : "";
}

function flatten(results) {
  return Array.prototype.concat.apply([], results);
}

function traverse(linkRel) {
  return (parents) => {
    if (!Array.isArray(parents)) {
      parents = [parents];
    }

    return Promise.all(
      parents.map((parent) => {
        const items = parent.items;
        if (!items) {
          console.error("Could not find items in response", parent);
          return [];
        }

        return Promise.all(
          items.map((item) => {
            const link = extractLink(item.links, linkRel);
            if (!link) {
              console.error(`No ${linkRel} found for item`, item);
              return [];
            }
            return axios.get(link).then((response) => {
              const data = response.data;
              data.items = data.items.map((child) => {
                child.parent = item;
                return child;
              });
              return data;
            });
          })
        ).then(flatten);
      })
    ).then(flatten);
  };
}

export default {
  components: {
    HardwareCatalogueFilters: HardwareCatalogueFilters,
  },
  data() {
    return {
      loading: true,
      panel: "search",
      allNodes: [],
      filteredNodes: [],
      searchQuery: "",
      searchStrict: false,
    };
  },
  methods: {
    async fetchNodes() {
      this.loading = true;
      this.allNodes = await axios
        .get("sites.json")
        .then(({ data }) => data)
        .then(traverse("clusters"))
        .then(traverse("nodes"))
        .then((results) => flatten(results.map(({ items }) => items)));
      this.filteredNodes = this.allNodes;
      this.loading = false;
      console.log(`Loaded ${this.allNodes.length} nodes`);
    },
    updateSearch() {},
    clearSearch() {},
    changeView(panel) {
      this.panel = panel;
    },
    reset() {
      this.filteredNodes = this.allNodes;
    },
    onFiltersChanged(filters) {
      if (!filters) {
        this.filteredNodes = this.allNodes;
        return;
      }

      this.filteredNodes = this.allNodes.filter((node) => {
        return filters.every((f) => f(node));
      });
    },
  },
  mounted() {
    this.fetchNodes();
  },
};
</script>
