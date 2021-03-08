import Glide from '@glidejs/glide'
require('@glidejs/glide/dist/css/glide.core.min.css')
require('@glidejs/glide/dist/css/glide.theme.min.css')
require('./frontpage_carousel.css')

new Glide('.glide', {
    type: 'carousel',
    startAt: 0,
    perView: 1,
    autoplay: 5000,
    hoverpause: true
}).mount()