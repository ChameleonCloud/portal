import Glide from '@glidejs/glide'

/* The following imports are just to auto-load CSS onto the page */
import GlideCoreCSS from '@glidejs/glide/dist/css/glide.core.min.css'
import GlideThemeCSS from '@glidejs/glide/dist/css/glide.theme.min.css'
import CarouselCSS from './frontpage_carousel.css'

const glide = new Glide('.glide', {
    type: 'carousel',
    startAt: 0,
    perView: 1,
    autoplay: 5000,
    hoverpause: true
}).mount();
