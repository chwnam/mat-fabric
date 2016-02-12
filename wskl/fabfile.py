# coding: utf-8

"""
일러두기
=======
Python2 를 사용한 fabric 스크립트입니다.

* git 을 인증 생략하고 사용하기 위해서는 미리 서버의 ssh 공개 키를 해당 서버에 등록하기 바랍니다.
* 사용 예:
    fab production deploy
    fab production reset
"""
from __future__ import print_function
from fabric.api import cd, env, run, task, prefix

import os
import sys

git_url = 'ssh://git@ssh.github.com:443/chwnam/woosym-korean-localization.git'

production_host = '115.68.110.13'
production_project_root = '/var/zpanel/hostdata/dabory/public_html/wp-content/plugins/woosym-korean-localization'
production_user = 'dabory'


def check_env():
    if not env.hosts:
        print('Specify environment first!\ne.g)\n\t$ fab production deploy', file=sys.stderr)
        sys.exit(1)


@task
def production(branch='master'):
    env.host_name = 'Dabory'
    env.branch = branch
    env.hosts = production_host
    env.project_root = production_project_root
    env.user = production_user


@task
def deploy():
    check_env()

    print('Deploying to server \'%s\'...' % env.host_name)

    with cd(env.project_root):
        with prefix('if [[ -n $SSH_ASKPASS ]]; then unset SSH_ASKPASS; fi'):
            run('git fetch')
            run('git checkout %s' % env.branch)
            run('git pull')


@task
def reset():
    check_env()

    print('All files in the project root \'%s\'will be DESTROYED! Are you sure? ' % env.project_root)
    q = raw_input('Yes/no ')

    if q != 'Yes':
        print('The answer is not \'Yes\'. Stop resetting.')
        sys.exit(0)

    run('rm -rf "%s"' % env.project_root)

    path = os.path.dirname(env.project_root)
    clone_name = os.path.basename(env.project_root)

    # git clone
    with cd(path):
        with prefix('if [[ -n $SSH_ASKPASS ]]; then unset SSH_ASKPASS; fi'):
            run('git clone "%s" "%s"' % (git_url, clone_name, ))
