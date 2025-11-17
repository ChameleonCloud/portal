<template>
  <div>
    <div class="row">
      <div class="col-md-12">
        <div v-if="loading">
          <div class="well">
            <h4>
              <span class="fa fa-refresh fa-spin"></span> Loading hardware...
            </h4>
          </div>
        </div>
        <div v-else>
          <div v-show="panel === 'search'">
            <HardwareCatalogueFilters
              ref="filters"
              v-bind:filteredNodes="filteredNodes"
              v-bind:allNodes="allNodes"
              v-on:filtersChange="onFiltersChanged"
            />

            <button
              class="btn btn-sm btn-info"
              v-on:click="changeView('results')"
            >
              View</button
            >{{ " " }}
            <button
              class="btn btn-sm btn-success"
              data-toggle="modal"
              data-target="#show-reservation"
            >
              Reserve</button
            >{{ " " }}
            <button class="btn btn-sm" v-on:click="reset()">Reset</button>
          </div>

          <div class="modal" tabindex="-1" role="dialog" id="show-reservation">
            <div class="modal-dialog" role="document">
              <div class="modal-content">
                <div class="modal-header">
                  <button
                    type="button"
                    class="close"
                    data-dismiss="modal"
                    aria-label="Close"
                  >
                    <span aria-hidden="true">&times;</span>
                  </button>
                  <h5 class="modal-title">Reserve from selection</h5>
                </div>
                <div class="modal-body">
                  <p>Using the Blazar CLI:</p>
                  <pre>
openstack reservation lease create \
  --reservation type=physical:host,min=1,max=1,resource_properties={{
                      reservationPropertiesJSON
                    }} \
  NAME_OF_LEASE
                  </pre>
                </div>
                <div class="modal-footer">
                  <button
                    type="button"
                    class="btn btn-secondary"
                    data-dismiss="modal"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>

          <section v-show="panel === 'results'">
            <div class="row">
              <div class="col-md-6">
                <div class="btn-group">
                  <button class="btn btn-sm" v-on:click="changeView('search')">
                    Back
                  </button>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group">
                  <input
                    type="text"
                    class="form-control"
                    name="nodeViewSearch"
                    v-on:input="updateSearch"
                    placeholder="Search by any node properties."
                  />
                </div>
              </div>
            </div>

            <div class="row">
              <div class="col-md-12">
                <div
                  v-if="Object.keys(groupedNodes).length > 1"
                  class="jump-to-site well well-sm"
                >
                  Nodes grouped by site, jump to a specific site:
                  <span v-for="(nodes, site) in groupedNodes" :key="site + '-link'">
                    <span @click="jumpToSite(site)" class="jump-to-site-link">{{ siteInfo[site] ? siteInfo[site].name : site }}</span>
                  </span>
                </div>

                <InfiniteScroller
                  ref="scroller"
                  :items="nodesWithSiteHeaders"
                  v-slot="{ item, index }"
                >
                  <h2
                    v-if="item.isHeader"
                    :id="'site-' + item.site"
                    class="site-header-container"
                  >
                    <span>
                      Site: {{ item.siteName }}
                      <span
                        v-if="index > 0"
                        @click="returnToTop"
                        class="return-to-top"
                        title="Return to top"
                        >↑</span
                      >
                    </span>
                    <a
                      v-if="siteCalendarLinks[item.site]"
                      :href="siteCalendarLinks[item.site]"
                      target="_blank"
                      class="availability-calendar-link"
                    >
                      View Host Calendar 📅
                    </a>
                  </h2>
                  <HardwareDetails v-else :hardware="item.node" />
                </InfiniteScroller>

                <div v-show="!visibleNodes.length" class="alert alert-warning">
                  Node(s) not found.
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.site-header-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.availability-calendar-link {
  text-decoration: none;
}

.availability-calendar-link:hover {
  text-decoration: underline;
}

.return-to-top {
  font-size: 22px;
  font-weight: bold;
  color: #000;
  cursor: pointer;
  margin-left: 0.5em;
  position: relative;
  top: -4px;
}

.jump-to-site-link {
  color: #337ab7;
  cursor: pointer;
  margin: 0 5px;
}
</style>

<script>
import axios from "axios";
import { capitalCase } from "change-case";
import HardwareCatalogueFilters from "./HardwareCatalogueFilters.vue";
import HardwareDetails from "./HardwareDetails.vue";
import InfiniteScroller from "./InfiniteScroller.vue";

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
    HardwareCatalogueFilters,
    HardwareDetails,
    InfiniteScroller,
  },
  data() {
    return {
      loading: true,
      panel: "search",
      searchQuery: "",
      allNodes: [],
      filteredNodes: [],
      visibleNodes: [],
      reservationProperties: [],
      siteInfo: {},
    };
  },
  computed: {
    calendarLinks() {
      const links = {};
      for (const siteId in this.siteInfo) {
        links[
          siteId
        ] = `${this.siteInfo[siteId].web}/project/leases/calendar/host/`;
      }
      return links;
    },
    siteCalendarLinks() {
      const links = {};

      // Get all unique node types across all visible nodes, filtering out undefined
      const allNodeTypes = new Set(
        this.visibleNodes
          .map((node) => node.nodeType)
          .filter((type) => type !== undefined)
      );
      const uniqueType =
        allNodeTypes.size === 1 ? allNodeTypes.values().next().value : null;
      const nodeTypeParam = uniqueType ? `?node_type=${uniqueType}` : "";

      for (const site in this.groupedNodes) {
        const baseUrl = this.calendarLinks[site];
        if (!baseUrl) {
          links[site] = "";
          continue;
        }

        links[site] = `${baseUrl}${nodeTypeParam}`;
      }
      return links;
    },
    reservationPropertiesJSON() {
      return JSON.stringify(this.reservationProperties);
    },
    groupedNodes() {
      return this.visibleNodes.reduce((acc, node) => {
        const site = node.parent.parent.uid;
        if (!acc[site]) {
          acc[site] = [];
        }
        acc[site].push(node);
        return acc;
      }, {});
    },
    nodesWithSiteHeaders() {
      const result = [];
      for (const site in this.groupedNodes) {
        const siteName = this.siteInfo[site] ? this.siteInfo[site].name : site;
        result.push({ isHeader: true, site: site, siteName: siteName, uid: site });
        this.groupedNodes[site].forEach((node) => {
          result.push({ isHeader: false, node: node, uid: node.uid });
        });
      }
      return result;
    },
  },
  methods: {
    capitalCase,
    async fetchSiteInfo() {
      try {
        const response = await axios.get("chameleon_sites.json");
        const sites = response.data.items;
        const siteInfo = {};
        for (const site of sites) {
          siteInfo[site.uid] = {
            web: site.web,
            name: site.name,
          };
        }
        this.siteInfo = siteInfo;
      } catch (error) {
        console.error("Failed to fetch site information:", error);
      }
    },
    async fetchNodes() {
      const deepValues = (obj) => {
        return Object.values(obj).reduce((acc, subObj) => {
          if (typeof subObj === "object" && subObj !== null) {
            acc = acc.concat(deepValues(subObj));
          } else if (typeof subObj === "string") {
            acc.push(subObj);
          }
          return acc;
        }, []);
      };

      this.loading = true;
      await this.fetchSiteInfo();
      this.allNodes = await axios
        .get("sites.json")
        .then(({ data }) => data)
        .then(traverse("clusters"))
        .then(traverse("nodes"))
        .then((results) => flatten(results.map(({ items }) => items)))
        .then((items) =>
          items.map((item) => {
            // Generate a search index
            item._searchIndex = deepValues(item).join("|").toLowerCase();
            return item;
          })
        );
      this.visibleNodes = this.filteredNodes = this.allNodes;
      this.loading = false;
    },
    changeView(panel) {
      this.panel = panel;
      // When going back to search, clear the results-view search query
      if (panel === "search") this.searchQuery = "";
    },
    updateVisibleNodes() {
      this.visibleNodes = this.filteredNodes.filter((node) => {
        return (
          !this.searchQuery ||
          node._searchIndex.includes(this.searchQuery.toLowerCase())
        );
      });
    },
    reset() {
      this.$refs.filters.reset();
    },
    onFiltersChanged(filters) {
      if (!filters) {
        this.filteredNodes = this.allNodes;
        return;
      }

      let filtered = this.allNodes;
      const constraints = [];
      let canUseConstraints = true;
      for (const filterFn of filters) {
        let result = filterFn(filtered);
        // A bit hacky, but we're unwrapping effectively a named tuple here.
        // Only the JSPath filters return such a type.
        let constraint = null;
        if (!Array.isArray(result)) {
          constraint = result.constraint;
          result = result.result;
        }

        filtered = result;
        if (constraint) {
          constraints.push(constraint);
        } else {
          canUseConstraints = false;
        }
      }

      if (canUseConstraints) {
        if (constraints.length <= 1) {
          this.reservationProperties = constraints.length ? constraints[0] : [];
        } else {
          this.reservationProperties = ["and", ...constraints];
        }
      } else {
        this.reservationProperties = [
          "in",
          // TODO: support just 'name' here...
          "$node_name",
          filtered.map(({ name, nodeName }) => name || nodeName),
        ];
      }

      this.filteredNodes = filtered;
      this.updateVisibleNodes();
    },
    updateSearch(event) {
      this.searchQuery = event.target.value;
      this.updateVisibleNodes();
    },
    jumpToSite(site) {
      const index = this.nodesWithSiteHeaders.findIndex(
        (item) => item.isHeader && item.site === site
      );
      if (index !== -1) {
        this.$refs.scroller.scrollToIndex(index);
      }
    },
    returnToTop() {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },
    capitalCase(str) {
      return capitalCase(str);
    },
  },
  mounted() {
    this.fetchNodes();
  },
};
</script>
