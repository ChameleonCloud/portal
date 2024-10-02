const glob = require('glob');
const path = require('path');
const BundleTracker = require('webpack-bundle-tracker');

const pages = glob.sync("*/vue/*.js").reduce((memo, file) => {
  memo[path.parse(file).name] = {
    entry: file,
    chunks: ['vendor'],
  };
  return memo
}, {});

const devHost = 'localhost';
const devPort = 9000;
const devMode = process.env.NODE_ENV !== 'production';

module.exports = {
  pages,
  filenameHashing: false,
  productionSourceMap: false,
  publicPath: devMode ? `http://${devHost}:${devPort}/` : '',
  outputDir: 'static/vue/',

  chainWebpack: config => {
    if (devMode) {
      config.devtool('source-map');
    }

    config.optimization
      .splitChunks({
        cacheGroups: {
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendor',
            chunks: 'all',
            priority: 1,
          },
        },
      });

    // Django is serving webpack bundles via its template engine; disable
    // Vue's automatic generation of HTML.
    Object.keys(pages).forEach(page => {
      config.plugins.delete(`html-${page}`);
      config.plugins.delete(`preload-${page}`);
      config.plugins.delete(`prefetch-${page}`);
    });

    config
      .plugin('BundleTracker')
      .use(BundleTracker, [{
        path: '/project',
        filename: 'webpack-stats.json'
      }]);

    config.resolve.alias
      .set('__STATIC__', 'static');

    config.devServer
      .public(`http://${devHost}:${devPort}`)
      .host('0.0.0.0')
      .port(devPort)
      .hotOnly(true)
      .watchOptions({poll: 1000})
      .https(false)
      .headers({'Access-Control-Allow-Origin': ['*']});
  }
};
