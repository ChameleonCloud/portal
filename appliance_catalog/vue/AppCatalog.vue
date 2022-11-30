<template>
  <div>
    <div class="form-group">
      <input class="form-control" type="text" placeholder="Search by name, description, or author">
      <div class="project-supported">
        <label for="filter.project_supported">Filter by <span
            class="label label-success">Chameleon Supported</span></label>&nbsp;
        <input id="filter.project_supported" type="checkbox" aria-label="Toggle Show">
      </div>
      <div>
        <span>Search by keywords</span><br>
        <span>Toggle switch</span>
      </div>
      <div>
        <input type="button" value="Search" class="btn btn-primary">
        <input type="button" value="Reset" class="btn btn-warning" style="margin-left:4px"/>
        <div class="btn-group pull-right" role="group" aria-label="View options">
          <button type="button" class="btn btn-default view-switch"
                  tooltip="Switch to grid view"
                  tooltip-placement="top"
                  tooltip-trigger="mouseenter"
                  tooltip-append-to-body="true"
          >
            <i class="fa fa-th-large"></i><span class="sr-only">Grid View</span>
          </button>
          <button type="button" class="btn btn-default view-switch"
                  tooltip="Switch to table view"
                  tooltip-placement="top"
                  tooltip-trigger="mouseenter"
                  tooltip-append-to-body="true"
          >
            <i class="fa fa-table"></i><span class="sr-only">Table View</span>
          </button>
        </div>
      </div>
    </div>

    <!-- <div class="well spinner">
      <h4><span class="fa fa-spinner fa-spin"></span> Loading appliances...</h4>
    </div> -->

    <div ng-show="!loading.appCatalog">
      <div ng-show="isEmpty(messages.appCatalog)">
        <div ng-show="!appliances || appliances.length < 1">
          <alert type="warning">There are no appliances. You can create one
            <a href="create/">here</a>.
          </alert>
        </div>
        <div ng-show="appliances && appliances.length > 0">
          <div ng-show="viewType=='grid'" ng-include="'template/grid.html/'"></div>
          <div ng-show="viewType=='table'" ng-include="'template/table.html/'"></div>
          <h4 ng-show="filteredAppliances && filteredAppliances.length > appsPerPage"
              class="pagination-header">
            <pagination boundary-links="true" total-items="filteredAppliances.length"
                        items-per-page="appsPerPage"
                        ng-model="appsCurrentPage" ng-change="appsPageChanged(appsCurrentPage)"
                        class="pagination-sm"
                        previous-text="&lsaquo;" next-text="&rsaquo;" first-text="&laquo;"
                        last-text="&raquo;"></pagination>
            <small class="pagination-summary">Showing [[getPageIndex()]] of
              [[filteredAppliances.length]]
              appliances
            </small>
          </h4>
        </div>
      </div>
      <div ng-show="!isEmpty(messages.appCatalog)">
        <alert ng-repeat="msg in messages.appCatalog" type="[[msg.type]]"></alert>
      </div>
    </div>
  </div>


</template>

<style scoped/>

<script>
export default {
  data() {}
}
</script>