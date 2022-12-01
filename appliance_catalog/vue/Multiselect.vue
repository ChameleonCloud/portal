<template>
  <div class="multiselect-wrapper">
    <Multiselect class="multiselect" :multiple="true" placeholder="Search by keywords" v-model="value"
                 :options="options"></Multiselect>
  </div>

</template>

<script>
    import Multiselect from 'vue-multiselect'

    export default {
        components: {Multiselect},
        data() {
            return {
                value: null,
                options: ['Altera', 'ansible', 'ARM64', 'bro', 'CentOS', 'clarkson', 'cuda', 'cuda Deep Learning Ubuntu']
            }
        }
    }
</script>

<style src="vue-multiselect/dist/vue-multiselect.min.css"></style>

<!-- Override package CSS with custom Chameleon-themed CSS-->
<style>
    .multiselect__tag {
        background: #74a93c;
    }

    .multiselect__option--highlight {
        background: #74a93c;
    }

    .multiselect__option--highlight:after {
        background: #74a93c;
    }

    .multiselect__option--selected.multiselect__option--highlight {
        background: #798b91;
    }

    .multiselect__option--selected.multiselect__option--highlight:after {
        background: #798b91;
    }

    .multiselect__tag-icon:hover {
        background: #74a93c;
    }

    .multiselect__input, .multiselect__single {
        padding: 0 0 0 0;
    }

    .multiselect__placeholder {
        margin-left:4px;
        color: #999999;
    }
</style>
