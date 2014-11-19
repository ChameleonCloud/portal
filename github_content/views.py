from django.shortcuts import render
import yaml
import os

def about( request ):
    content_dir = os.path.join( os.path.dirname( __file__ ), 'content')
    fh = open( os.path.join( content_dir, '_data', 'team.yml' ) )
    team = yaml.load( fh )
    fh.close()

    context = {
        'site': {
            'baseurl': '/static/',
            'data': {
                'team': team
            }
        }
    }

    return render( request, 'about.html', context, dirs=(content_dir, os.path.join( content_dir, '_includes' ),) )
