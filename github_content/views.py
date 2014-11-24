from django.shortcuts import render
from django.http import HttpResponse
from django.http import Http404
from django.core.servers.basehttp import FileWrapper
import yaml
import os

content_dir = os.path.join( os.path.dirname( __file__ ), 'content' )

def about( request ):
    fh = open( os.path.join( content_dir, '_data', 'team.yml' ) )
    team = yaml.load( fh )
    fh.close()

    for member in team:
        member['image'] = member['image'][1:]

    return render( request, 'github_content/about.html', { 'team': team, 'title': 'About' } )

def _parse_jekyll( content ):
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

def nsf_cloud_workshop( request ):
    fh = open( os.path.join( content_dir, 'NSFCloudWorkshop', 'index.md' ) )
    jekyll_content = fh.read()
    fh.close()

    meta, content = _parse_jekyll( jekyll_content )
    meta['image'] = meta['image'][1:]

    context = {
        'meta': meta,
        'content': content,
    }
    return render( request, 'github_content/markdown_page.html', context )

def nsf_cloud_workshop_agenda( request ):
    response = HttpResponse(
        FileWrapper( open( os.path.join( content_dir, 'NSFCloudWorkshop', 'NSFCloud Workshop Tentative Agenda.pdf' ) ) ),
        content_type='application/pdf'
    )
    response['Content-Disposition'] = 'attachment; filename=%s' % 'NSFCloud Workshop Tentative Agenda.pdf'
    return response

def news( request ):

    posts = []
    posts_dir = os.path.join( content_dir, '_posts' )
    for post in os.listdir( posts_dir ):
        fh = open( os.path.join( posts_dir, post ) )
        jekyll_content = fh.read()
        fh.close()
        meta, content = _parse_jekyll( jekyll_content )
        if 'image' in meta:
            meta['image'] = meta['image'][1:]

        meta['url'] = '/'.join( os.path.splitext( post )[0].split( '-', 3 ) )

        posts.append( ( meta, content, ) )

    posts.reverse()

    context = {
        'title': 'News',
        'posts': posts
    }

    return render( request, 'github_content/news.html', context )

def news_story( request, year, month, day, slug ):
    post_name = '{0}-{1}-{2}-{3}.md'.format(year, month, day, slug)
    print post_name
    try:
        fh = open( os.path.join( content_dir, '_posts', post_name ) )
        jekyll_content = fh.read()
        fh.close()
    except:
        try:
            post_name = '{0}-{1}-{2}-{3}.markdown'.format(year, month, day, slug)
            fh = open( os.path.join( posts_dir, post_name ) )
            jekyll_content = fh.read()
            fh.close()
        except:
            raise Http404

    meta, content = _parse_jekyll( jekyll_content )
    context = {
        'title': meta.get('title'),
        'author': meta.get('author'),
        'date': meta.get('date'),
        'content': content
    }

    if 'image' in meta:
        context['image'] = meta.get('image')[1:]

    return render( request, 'github_content/news_story.html', context )
