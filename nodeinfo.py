#!/usr/bin/env python2
# vim: set syntax=python nospell:
# ########################
# nodeinfo.py
# bootle app for cli or wsgi
# companionway.net
#
#
# This script can be run from the commandline as is or through WSGI
# ########################
"""
nodeinfo.py
requires: bottle.py
for auto install (gwm): use fab -H<myhost> webit
To run from webserver (eg apache2) - this is out of fabfile.py file that I use...
# install wsgi, web.py, and config wsgi alias /chkit/nodeinfo  # note: uses python2 !!
      sudo('apt install python-pip')
      put('/home/geoffm/dev/www/skel/wsgi.conf', '/etc/apache2/conf-available/', use_sudo=True)
      # sudo('pip install web.py')
      sudo('pip install bottle')
      sudo('apt install libapache2-mod-wsgi')
      sudo('a2enmod wsgi')
      sudo('a2enconf wsgi')
      sudo('systemctl restart apache2')
# ## or ###
sudo pip install python pip bottle
sudo apt install libapache2-mod-wsgi
sudo a2enmod wsgi
# with the proper permissions:
#  scp /home/geoffm/dev/www/skel/wsgi.conf remote_host:/etc/apache2/conf-available/
sudo a2enconf wsgi
sudo systemctl restart apache2
# #####################
## Contents of wsgi.conf: ##
# http://<servername>/chkit/nodeinfo
WSGIScriptAlias /chkit/nodeinfo /var/www/html/chkit/nodeinfo.py/
<directory /usr/local/www/wsgi-scripts>
  <IfVersion < 2.4>
    Order allow,deny
    Allow from all
  </IfVersion>

  <IfVersion >= 2.4>
    Require all granted
  </IfVersion>
</Directory>
"""
# ###########################

# imports #
import socket
import subprocess
import shlex
import os
import sys
import datetime
from bottle import default_app, route, run, request, SimpleTemplate


# setup environment #
os.chdir(os.path.dirname(__file__))
sys.path.append(os.path.dirname(__file__))
# from wraphtml import WrapHtml


# WSGI #
# the name "application" is needed for wsgi
application = default_app()


# globals #
tpl = SimpleTemplate("""
    <html>
    <head>
        <style>
            body {
                    background: #000;
            }
            .container {
                    background: -webkit-linear-gradient(top, #ACBDC8 0.0%, #6C7885 100.0%) no-repeat;
                    border: 3px solid #333;
            }
            .center_box {
                    // `font-family: Philosopher;
                    background-color: lightgrey;
                    margin: auto;
                    width: 75%;
                    border: 3px solid black;
                    padding: 10px;
                    margin-top: 20px;
                    margin-bottom: 20px;
                    }
            h2 {
                    // font-family: Helvetica;
                    font-family: Architects Daughter;
                    text-align: center;
            }
            div.title {
            margin-left: 5px;
            margin-right: 5px;
            margin-top: 10px;
            border-top: solid black 3px;
            text-align: center;
            font-size: 35px;
            border-bottom: solid black 2px;
            margin-bottom: 4px;
            }
            table, th, td {
                border: 1px solid black;
            }
            .grid-container {
                display: grid;
                grid-template-columns: auto auto auto;
            }
            .grid-item {
                text-align: center;
            }
           .footer {
                border-top: solid lightgrey 1px;
                padding-top: 3px;
                padding-left: 3px;
                padding-right: 3px;
                margin-right: 5px;
                margin-left: 5px;
                color: white;
                padding-bottom: 3px;
                border-bottom: solid lightgrey 1px;
                margin-bottom: 1px;
            }
               .rc_nav {
                overflow: hidden;
                background-color: #363841;
                text-align: center;
                z-index: 6;
                margin: 4px 4px 4px 4px;
              }
              .rc_nav a {
                display: inline-block;
               margin-right: -4px;  /* inline-block gap fix */
               color: #fff;
               padding: 5px 10px 5px 10px;
               text-decoration: none;
               font-family: Poppins;
               font-size: 16px;
               -webkit-transition: background 0.3s linear;
               -moz-transition: background 0.3s linear;
               -ms-transition: background 0.3s linear;
               -o-transition: background 0.3s linear;
               transition: background 0.3s linear;
               z-index: 9;
          }
          .rc_nav a:hover {
            background-color: #575b69;
            color: #bdfe0e2;
          }
          .rc_nav .icon {
            display: none;
          }

            .rc_content {
              text-align: center;
              padding-left:14px;
              font-family: Poppins;
              margin-top: 100px;
              color: #8e909b;
             }
            @media screen and (max-width: 820px) {
              .rc_nav a {display: none;}
              .rc_nav a.icon {
              float: right;
              display: block;
              width: 60px;
              }
            }
            @media screen and (max-width: 820px) {
              .rc_nav.responsive {position: relative; top: 73px;}
              .rc_nav.responsive .icon {
              position: fixed;
              right: 0;
              top: 0;
            }
            .rc_nav.responsive a {
              float: none;
              display: block;
              text-align: center;
            }
        }
        </style>
    </head>
    <body>
      <div class='container'>
        <div class='title'>
        {{title}}
        </div>
          <!-- Top navigation -->
      %if nav_d:
      <!--
      <div id="rc_logo">
        <a href="/" title="Organization">{{org}}</a>
      </div>
      -->
      <div class="rc_nav">
        % for k,v in nav_d.iteritems():
                 <a href="{{v}}">{{k}}</a>
        % end
      </div>
      <br>
      % end

        <div class='center_box'>
          {{!content}}
        </div>
        <div class='footer'>
          <div class='grid-container'>
          <div class='grid-item' style='text-align: left;'>  {{!left}}  </div>
          <div class='grid-item' style='text-align: center'> {{center}} </div>
          <div class='grid-item' style='text-align: right;'> {{right}}  </div>
          </div> <!-- class=grid-container -->
        </div> <!-- class=footer -->
    </div class='container'>
    </body>
    </html>
""")

# these are used to filter out warnings and errors from inxi
#   - see def acceptible below
reject_strings = [
            "Use of uninitialized value",
            "Error",
            "print()",
            ]


# functions #
def acceptable(line):
    """
    determines if the line is acceptible based
    on a list of unacceptible strings (reject_strings)
    expects to find global defined reject_strings
    """
    for string in reject_strings:
        if string in line:
            return False  # line is not acceptable
    return True  # line is acceptible
    # end of def acceptible(line) #


def run_cmd(cmd, ret_type="str"):
    """
    run a command and return either a str or a list
    """
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0]
    # proc is now a list of lines
    if ret_type != "str":
        return proc.split("\n")
    return proc
    # end of def run_cmd(cmd, ret_type="str") #


# classes #
class HtmlWrap:
    """
    This is basically and unskillfully used as a data container.
    Purpose: Allows setting of template vars and then renders the template when requested
    for the most part this class is just a data container (python2)
    there is not a real need for unique instance values - it gets set, and then called once, then dies with the end of a page rendering
    Use:
    @route('/')
    def index():
        content = "My Content"
        page = HtmlWrap(content=content,
                        title="System Info",
                        center="Awesome!")  # instantiates a class named page and sets the content
        page.org = "my.org"         # example
        return page.render()        # returns a template driven rendered html page
    """
    def __init__(self, content="I need content!", title="Title", center="Enjoy!", nav_d={}):
        self.content = content
        self.title = title
        self.nav_d = nav_d

        # footer vars
        self.org = "companionway.net"
        self.year = datetime.datetime.now().strftime('%Y')
        self.dtime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

        self.left = self.org + " &copy; " + self.year
        self.center = center
        self.right = self.dtime

    def render(self):
        """
        render the html page using the var values inserted into global template (tpl)
        """
        output = tpl.render(title=self.title,
                            content=self.content,
                            nav_d=self.nav_d,
                            left=self.left,
                            center=self.center,
                            right=self.right,
                            org=self.org,)
        return output
    # end of class HtmlWrap #


# routes #
@route('/')
def index():
    """
    default route
    """
    content = ""  # initialiaze var
    hostinfo = socket.gethostbyname_ex(socket.gethostname())
    # deal with None type when run from CLI ...
    request_uri = request.environ.get('REQUEST_URI') if request.environ.get('REQUEST_URI') is not None else ""
    lines = [
        ['Remote IP:', request.environ.get('REMOTE_ADDR')],
        ['IP Address:', str(hostinfo[2])],
        ['Server Port:', request.environ.get('SERVER_PORT')],
        ['File:', os.path.basename(__file__)],
        ['Request URI:', request.environ.get('REQUEST_URI')],
        ['Document Root:', str(request.environ.get('DOCUMENT_ROOT'))],
        ['Referer:', request.environ.get('HTTP_REFERER')],
        ['HTTPS Protocol:', request.environ.get('HTTPS')],
        ['Server Software:', request.environ.get('SERVER_SOFTWARE')],
        ['Server Admin:', request.environ.get('SERVER_ADMIN')],
        ['uptime:', str(subprocess.check_output(shlex.split("uptime")).decode("utf-8"))],
        ['uname -a:', str(subprocess.check_output(shlex.split("uname -a")).decode("utf-8"))],
        ['User Agent:', request['HTTP_USER_AGENT']],
        # ['top:', "<br>" + run_cmd("top -bn 1 | head").replace('\n','<br>')],
        ['<hr>Date Time:', datetime.datetime.now().strftime('%Y%m%d-%H:%M')],
        ]

    for line in lines:
        content += "<b>" + str(line[0]) + "</b> " + str(line[1]) + "<br>"
    page = HtmlWrap(content=content, title="System Info")
    page.nav_d = {'Home': '/',
                  "inxi": request_uri + '/inxi',
                  "inxifull": request_uri + '/inxifull'
                  }
    return page.render()


@route('/<new_route>')
def new_route(new_route):
    """
    This is a way to maintain use in as both a CLI application and a WSGI application in that the routes
    don't have to get muddled when you use a WSGIAlias with a subdir.
    All this does is take the route supplied to the script (that is not the root "/" and to match it to
    any routes we want. Then it builds the content desired based on that route and finally runs it through HtmlWrap class
    which fills in defaults or set variables and pumps it through a template to return the html.
    Because all the routes are build directly off of the original requestes uri we can easily work with that to
    construct other routes (as seen in the nav_d).
    """
    content = cmd = ""  # initialiaze vars
    # deal with None type when run from CLI ... yes, this is slightly different from above but it is because CLI doesn't like "" here.
    request_uri = request.environ.get('REQUEST_URI') if request.environ.get('REQUEST_URI') is not None else "/"
    base_request_uri = request_uri.replace("/" + new_route, '')  # for use in nav_d
    if new_route == "inxi":
        cmd = "inxi -F -c0"  # make sure you include -c0 for no ansi color codes which messes up html
    elif new_route == "inxifull":
        cmd = "inxi -wiFoldc0"
    else:
        content += "Not sure what you want... check your requested uri of [" + request_uri + "] please."
    if cmd != "":
        proc = run_cmd(cmd, "list")  # list is needed to make filtering easier (next step)
        lines = [line for line in proc if acceptable(line)]  # gotta love list comprehensions
        content += "<pre>" + "\n".join(lines) + "</pre>"  # maintains the output format and end of line feeds
    page = HtmlWrap(content=content, title="System Info", center=cmd)
    page.nav_d = {"nodeinfo": base_request_uri,
                  "inxi": base_request_uri + '/inxi',
                  "inxifull": base_request_uri + '/inxifull'
                  }
    return page.render()


if __name__ == '__main__':
    run(port=8080, debug=True, reloader=True)
