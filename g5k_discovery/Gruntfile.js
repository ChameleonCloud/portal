'use strict';
module.exports = function(grunt) {

    require('load-grunt-tasks')(grunt);
    require('time-grunt')(grunt);

    //Configurable paths for the application
    var appConfig = {
        app: require('./bower.json').appPath || '.',
        dist: require('./bower.json').distPath || 'static/g5k_discovery'
    };

    // Project configuration.
    grunt.initConfig({
        yeoman: appConfig,
        clean: {
            all: [
                '.tmp/*',
                '<%= yeoman.dist %>/js/*',
                '<%= yeoman.dist %>/css/*'
            ]
        },

        // Add vendor prefixed styles
        autoprefixer: {
            options: {
                browsers: ['last 2 versions']
            },
            dist: {
                files: [{
                    expand: true,
                    cwd: '.tmp/css/',
                    src: '{,*/}*.css',
                    dest: '.tmp/css/'
                }]
            }
        },

        compass: {
            options: {
                sassDir: '<%= yeoman.app %>/sass',
                cssDir: '.tmp/css',
                imagesDir: '<%= yeoman.dist %>/images',
                javascriptsDir: '<%= yeoman.dist %>/js',
                fontsDir: '<%= yeoman.dist %>/fonts',
                importPath: 'bower_components',
                relativeAssets: true
            },
            dist: {},
            dev: {
                options: {
                    debugInfo: true
                }
            }
        },

        cssmin: {
            dist: {
                files: {
                    '<%= yeoman.dist %>/css/main.css': [
                        '.tmp/css/custom.css',
                        'bower_components/angular-bootstrap-toggle-switch/style/bootstrap3/angular-toggle-switch-bootstrap-3.css'
                    ]
                }
            }
        },

        // ngmin tries to make the code safe for minification automatically by
        // using the Angular long form for dependency injection. It doesn't work on
        // things like resolve or inject so those have to be done manually.
        ngmin: {
            dist: {
                files: [{
                    expand: true,
                    cwd: '.tmp/concat/scripts',
                    src: '*.js',
                    dest: '.tmp/scripts'
                }]
            }
        },

        // Make sure code styles are up to par and there are no obvious mistakes
        jshint: {
            options: {
                jshintrc: '.jshintrc',
                reporter: require('jshint-stylish')
            },
            all: [
                'Gruntfile.js',
                '<%= yeoman.app %>/scripts/{,*/}*.js'
            ],
            test: {
                options: {
                    jshintrc: '.jshintrc'
                },
                src: ['tests/js/{,*/}*.js']
            }
        },

        copy: {
            dist: {
                files: [{
                        expand: true,
                        flatten: true,
                        cwd: '.',
                        src: 'bower_components/bootstrap-sass-official/assets/fonts/bootstrap/*',
                        dest: '<%= yeoman.dist %>/fonts/bootstrap'
                    }
                    /*,{
                              expand: true,
                              flatten: true,
                              cwd: '.',
                              src: 'bower_components/font-awesome/fonts/*',
                              dest: '<%= yeoman.dist %>/fonts'
                              }*/
                ]
            }
        },

        concat: {
            vendor: {
                src: [
                    'bower_components/json3/lib/json3.js',
                    'bower_components/underscore/underscore.js',
                    'bower_components/momentjs/moment.js',
                    'bower_components/angular/angular.js',
                    'bower_components/angular-bootstrap/ui-bootstrap-tpls.js',
                    'bower_components/zeroclipboard/dist/ZeroClipboard.js',
                    'bower_components/ng-clip/src/ngClip.js',
                    'bower_components/angular-bootstrap-toggle-switch/angular-toggle-switch.js'
                ],
                dest: '.tmp/scripts/vendor.js'
            },
            scripts: {
                src: [
                    '<%= yeoman.app %>/scripts/*.js',
                    '<%= yeoman.app %>/scripts/controllers/*.js'
                ],
                dest: '.tmp/concat/scripts/scripts.js'
            }
        },

        uglify: {
            /*options: {
                mangle: false
              },*/
            dist: {
                files: {
                    '<%= yeoman.dist %>/js/vendor.js': ['.tmp/scripts/vendor.js'],
                    '<%= yeoman.dist %>/js/main.js': ['.tmp/scripts/scripts.js']
                }
            }
        },

        karma: {
            unit: {
                configFile: 'tests/js/karma.conf.js'
            }
        }
    });
    grunt.registerTask('build', [
        'clean',
        'compass:dist',
        'autoprefixer',
        'concat',
        'ngmin',
        'copy:dist',
        'cssmin',
        'uglify'
    ]);

    grunt.registerTask('default', [
        'newer:jshint',
        'build',
        //'karma'
    ]);
};
