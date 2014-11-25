from django.core.urlresolvers import reverse
import yaml
import os

content_dir = os.path.join( os.path.dirname( __file__ ), 'content' )

def parse_jekyll( content ):
    meta = []
    rest = []
    in_header = False
    for line in content.splitlines():
        if in_header:
            if line == '---':
                in_header = False;
            else:
                meta.append( line )
        elif line == '---':
            in_header = True
        else:
            rest.append( line )

    return (yaml.load( '\n'.join( meta ) ), '\n'.join( rest ))

def get_posts( limit=None ):
    posts = []
    posts_dir = os.path.join( content_dir, '_posts' )
    files = os.listdir( posts_dir )
    files.reverse()
    if limit:
        files = files[0:limit]

    for post in files:
        fh = open( os.path.join( posts_dir, post ) )
        jekyll_content = fh.read()
        fh.close()
        meta, content = parse_jekyll( jekyll_content )
        if 'image' in meta:
            meta['image'] = meta['image'][1:]

        args = os.path.splitext( post )[0].split( '-', 3 )
        meta['url'] = reverse( 'github_content.views.news_story', args=args )

        posts.append( { 'meta': meta, 'content': content, 'teaser': content.split('<!--more-->')[0] } )

    return posts
