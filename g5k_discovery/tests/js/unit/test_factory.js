'use strict';
/*global it, xit, expect, xdescribe, beforeEach, afterEach, inject, jasmine, getJSONFixture, _ */
xdescribe('UtilFactory', function() {

    var UtilFactory;

    beforeEach(function() {
        module('discoveryApp');
    });

    beforeEach(inject(function(_UtilFactory_) {
        UtilFactory = _UtilFactory_;
    }));

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
    it('Converts plain words to proper form', function() {
        var result = UtilFactory.snakeToReadable('test string');
        expect(result).toEqual('Test string');
    });
    it('Converts snakecase to proper form', function() {
        var result = UtilFactory.snakeToReadable('test_string');
        expect(result).toEqual('Test String');
    });
    it('Keeps proper form intact', function() {
        var result = UtilFactory.snakeToReadable('Test String');
        expect(result).toEqual('Test String');
    });
});

xdescribe('ResourceFactory', function() {
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

    beforeEach(function() {
        module('discoveryApp');
    });

    beforeEach(inject(function(_ResourceFactory_, _$httpBackend_) {
        ResourceFactory = _ResourceFactory_;
        $httpBackend = _$httpBackend_;
        jasmine.getJSONFixtures().fixturesPath='base/unit/fixtures';
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

    xit('Formats node', function() {
        var node = getJSONFixture('node.json');
        var formattedNode = getJSONFixture('formatted_node.json');
        ResourceFactory.formatNode(node);
        expect(node).toEqual(formattedNode);
    });

    it('Prune Filters', function() {
        ResourceFactory.filters = angular.copy(filters);
        ResourceFactory.pruneFilters();
        expect(ResourceFactory.filters).toEqual(prunedFilters);
    });

    it('Process Nodes', function() {
        ResourceFactory.filters = {};
        var formattedNode = getJSONFixture('formatted_node.json');
        var filters = getJSONFixture('filters.json');
        ResourceFactory.processNodes([formattedNode, formattedNode]);
        expect(ResourceFactory.filters).toEqual(filters);
    });

});
