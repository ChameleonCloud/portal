'use strict';
/*global it, expect, describe, beforeEach, afterEach, inject, jasmine, getJSONFixture, _, moment */
describe('UtilFactory', function() {

    var UtilFactory;

    beforeEach(function() {
        module('underscore');
        module('moment');
        module('discoveryApp');
    });

    beforeEach(inject(function(_UtilFactory_) {

        UtilFactory = _UtilFactory_;
        UtilFactory.nameMap = {
            'smp_size': '# CPUs',
            'smt_size': '# Cores',
            'architecture~smt_size:48': 'Compute Nodes',
            'network_adapters~4~interface:InfiniBand': 'With Infiniband Support'
        };
        UtilFactory.sizeMap = {
            '128 GiB': 134956859392,
            '500 GB': 500107862016,
            '1 TB': 1000204886016
        };
        UtilFactory.tagMap = {
            'architecture~smt_size:48': 'Compute Nodes',
            'network_adapters~4~interface:InfiniBand': 'With Infiniband Support'
        };
    }));

    it('Checks if value tag should be shown', function() {
        var result = UtilFactory.isShowValTag('network_adapters~4~interface', 'InfiniBand');
        expect(result).toEqual(false);
        result = UtilFactory.isShowValTag('some-string');
        expect(result).toEqual(true);
    });

    it('Should return byte size value', function() {
        var result = UtilFactory.humanizedToBytes('128 GiB');
        expect(result).toEqual(134956859392);
        result = UtilFactory.humanizedToBytes('500 GB');
        expect(result).toEqual(500107862016);
        result = UtilFactory.humanizedToBytes('1 TB');
        expect(result).toEqual(1000204886016);
        result = UtilFactory.humanizedToBytes('1 KiB');
        expect(result).toEqual(1024);
        result = UtilFactory.humanizedToBytes('1 MiB');
        expect(result).toEqual(1024 * 1024);
        result = UtilFactory.humanizedToBytes('1 GiB');
        expect(result).toEqual(1024 * 1024 * 1024);
        result = UtilFactory.humanizedToBytes('1 TiB');
        expect(result).toEqual(1024 * 1024 * 1024 * 1024);
        result = UtilFactory.humanizedToBytes('1 KHz');
        expect(result).toEqual(1000);
        result = UtilFactory.humanizedToBytes('1 MHz');
        expect(result).toEqual(1000 * 1000);
        result = UtilFactory.humanizedToBytes('1 GHz');
        expect(result).toEqual(1000 * 1000 * 1000);
        result = UtilFactory.humanizedToBytes('1 THz');
        expect(result).toEqual(1000 * 1000 * 1000 * 1000);
    });

    it('Should scale to appropriate memory size', function() {
        var result = UtilFactory.scaleMemory(1024);
        expect(result).toEqual('1.00 KiB');
        result = UtilFactory.scaleMemory(1024 * 1024);
        expect(result).toEqual('1.00 MiB');
        result = UtilFactory.scaleMemory(1024 * 1024 * 1024);
        expect(result).toEqual('1.00 GiB');
        result = UtilFactory.scaleMemory(1024 * 1024 * 1024 * 1024);
        expect(result).toEqual('1.00 TiB');

    });

    it('Should scale to appropriate frequency size', function() {
        var result = UtilFactory.scaleFrequency(1000);
        expect(result).toEqual('1.00 KHz');
        result = UtilFactory.scaleFrequency(1000 * 1000);
        expect(result).toEqual('1.00 MHz');
        result = UtilFactory.scaleFrequency(1000 * 1000 * 1000);
        expect(result).toEqual('1.00 GHz');
        result = UtilFactory.scaleFrequency(1000 * 1000 * 1000 * 1000);
        expect(result).toEqual('1.00 THz');

    });

    it('Checks if undefined is an empty object', function() {
        var result = UtilFactory.isEmpty();
        expect(result).toEqual(true);
    });

    it('Checks if string is an empty object', function() {
        var result = UtilFactory.isEmpty('test');
        expect(result).toEqual(false);
    });

    it('Checks if integer is an empty object', function() {
        var result = UtilFactory.isEmpty(1);
        expect(result).toEqual(false);
    });
    it('Checks if [] is an empty object', function() {
        var result = UtilFactory.isEmpty([]);
        expect(result).toEqual(true);
    });
    it('Checks if {} is an empty object', function() {
        var result = UtilFactory.isEmpty({});
        expect(result).toEqual(true);
    });
    it('Checks if [1] is an empty object', function() {
        var result = UtilFactory.isEmpty([1]);
        expect(result).toEqual(false);
    });
    it('Checks if {test: "test"} is an empty object', function() {
        var result = UtilFactory.isEmpty({
            test: 'test'
        });
        expect(result).toEqual(false);
    });
    it('Converts keys to map values if present', function() {
        var result = UtilFactory.snakeToReadable('smp_size');
        expect(result).toEqual('# CPUs');
    });
    it('Converts plain words to proper form', function() {
        var result = UtilFactory.snakeToReadable('test string');
        expect(result).toEqual('Test string');
    });
    it('Converts snakecase to proper form', function() {
        var result = UtilFactory.snakeToReadable('test_string~test');
        expect(result).toEqual('Test String Test');
    });
    it('Keeps proper form intact', function() {
        var result = UtilFactory.snakeToReadable('Test String');
        expect(result).toEqual('Test String');
    });
    it('Should give merged date and time string', function() {
        var result = UtilFactory.getFormattedDate(moment('2015-01-31'), moment('2015-01-10 15:10:00'));
        //converts local to utc
        expect(result).toEqual('2015-01-31 21:10');
    });
});

describe('ResourceFactory', function() {
    var ResourceFactory, $httpBackend;
    var sites = {
        items: [{
            uid: 'tacc',
            links: [{
                href: '/sites/tacc/clusters',
                rel: 'clusters'
            }]
        }]
    };
    var clusters = {
        items: [{
            uid: 'alamo',
            links: [{
                href: '/sites/tacc/clusters/alamo/nodes',
                rel: 'nodes'
            }]
        }, {
            uid: 'chameleon',
            links: [{
                href: '/sites/tacc/clusters/chameleon/nodes',
                rel: 'nodes'
            }]
        }]
    };
    var alamoNodes = {
        items: [{
            uid: 1,
            site: 'tacc',
            cluster: 'alamo'
        }, {
            uid: 2,
            site: 'tacc',
            cluster: 'alamo'
        }]
    };

    var chameleonNodes = {
        items: [{
            uid: 3,
            site: 'tacc',
            cluster: 'chameleon'
        }, {
            uid: 4,
            site: 'tacc',
            cluster: 'chameleon'
        }]
    };

    var filters = {
        site: {
            tacc: [1, 2, 3, 4],
            uc: []
        },
        network_adapters: [{
            rate: {
                1.00: [1, 2, 3],
                10.00: [4]
            }
        }, {
            rate: null
        }]
    };
    var prunedFilters = {
        site: {
            tacc: [1, 2, 3, 4]
        },
        network_adapters: [{
                rate: {
                    1.00: [1, 2, 3],
                    10.00: [4]
                }
            },
            undefined
        ]
    };
    var appliedFilters = {
        site: {
            tacc: true
        },
        network_adapters: [{
            rate: {
                1.00: true
            }
        }]
    };
    var flatAppliedFilters = {
        'site': 'tacc',
        'network_adapters~0~rate': '1'
    };

    beforeEach(function() {
        module('discoveryApp');
    });

    beforeEach(inject(function(_ResourceFactory_, _$httpBackend_) {
        ResourceFactory = _ResourceFactory_;
        $httpBackend = _$httpBackend_;
        jasmine.getJSONFixtures().fixturesPath = 'base/unit/fixtures';
    }));

    afterEach(function() {
        //
    });

    it('Fetches sites, clusters, and nodes', function() {
        var scope = {};
        $httpBackend.when('GET', 'sites.json').respond(sites);
        $httpBackend.when('GET', 'sites/tacc/clusters.json').respond(clusters);
        $httpBackend.when('GET', 'sites/tacc/clusters/alamo/nodes.json').respond(alamoNodes);
        $httpBackend.when('GET', 'sites/tacc/clusters/chameleon/nodes.json').respond(chameleonNodes);
        ResourceFactory.getResources(scope, function() {
            var allNodes = _.union(alamoNodes.items, chameleonNodes.items);
            expect(ResourceFactory.allNodes).toEqual(allNodes);
        });
        $httpBackend.flush();
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
    });

    it('Formats node', function() {
        var node = getJSONFixture('node.json');
        var formattedNode = getJSONFixture('formatted_node.json');
        ResourceFactory.formatNode(node);
        expect(node).toEqual(formattedNode);
    });

    it('Prunes Filters', function() {
        ResourceFactory.filters = angular.copy(filters);
        ResourceFactory.pruneFilters();
        expect(ResourceFactory.filters).toEqual(prunedFilters);
    });

    it('Flattens Filters', function() {
        ResourceFactory.flatten(appliedFilters);
        expect(ResourceFactory.flatAppliedFilters).toEqual(flatAppliedFilters);
    });

    it('Process Nodes', function() {
        ResourceFactory.filters = {};
        var formattedNode = getJSONFixture('formatted_node.json');
        var filters = getJSONFixture('filters.json');
        ResourceFactory.processNodes([formattedNode, formattedNode]);
        expect(ResourceFactory.filters).toEqual(filters);
    });
});

describe('UserSelectionsFactory', function() {
    var UserSelectionsFactory;
    var dateS = moment();
    dateS.hours(15);
    dateS.minutes(0);
    dateS.seconds(0);
    dateS = moment(dateS).format('YYYY-MM-DDTHH:mm:ss') + 'Z';
    var userSelections = {
        startDate: '',
        startTime: dateS,
        endDate: '',
        endTime: dateS,
        minNode: '',
        maxNode: ''
    };
    beforeEach(function() {
        module('moment');
        module('discoveryApp');
    });

    beforeEach(inject(function(_UserSelectionsFactory_) {
        UserSelectionsFactory = _UserSelectionsFactory_;
        UserSelectionsFactory.userSelections = null;
    }));

    it('Should initialize user selections.', function() {
        UserSelectionsFactory.userSelectionsInit();
        expect(UserSelectionsFactory.userSelections).toEqual(userSelections);
    });
    it('Should get user selections.', function() {
        UserSelectionsFactory.getUserSelections();
        expect(UserSelectionsFactory.userSelections).toEqual(userSelections);
    });
});
