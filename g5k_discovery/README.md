# g5k_discovery
Chameleon Resource Discovery

## Description

This app provides a visual interface to filter nodes based on various criteria such as site, cluster, ram size, CPU cores etc. After filtering, users can generate a reservation script by providing additional info: reservation start date, reservation end date, maximum nodes requested and minimum nodes requested. This app is available at url: `/admin/allocations/`. 

## Installation
In a production environment dependencies are pre-built; no installation is required. In development, you can install dependencies as follows:

	cd g5k_discovery
	npm install
	bower install
	grunt

`grunt` command above runs js tests. Django tests can be run as follows:
	
	//to do

## Author
* Ajit Gauli <agauli@tacc.utexas.edu>