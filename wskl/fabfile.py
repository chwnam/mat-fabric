# coding: utf-8

"""
일러두기
=======
Python2 를 사용한 fabric 스크립트입니다.

* git 을 인증 생략하고 사용하기 위해서는 미리 개발 PC의 ssh 공개 키를 서버에 등록하기 바랍니다.
* git 의 pull 인증 절차를 생략하기 위해서는 github.com 에서 deployment 만을 위한 키를 등록하기 바랍니다.

* 사용 예:
    fab production deploy
    fab production reset
    fab test deploy
    fab test reset

* 만약 브랜치를 deploy 하고 싶다면 다음과 같이 하면 됩니다.
    fab test:branch=<branch-name> deploy
"""
from __future__ import print_function
from fabric.api import cd, env, hosts, run, task, prefix
from fabric.contrib.files import exists as remote_exists
from fabric.colors import red, green

import os
import re
import sys

git_url = 'ssh://git@ssh.github.com:443/chwnam/woosym-korean-localization.git'

test_host = '115.68.110.13'
test_project_root = '/var/zpanel/hostdata/mbm/public_html/wp-content/plugins/woosym-korean-localization'
test_user = 'dabory'

production_host = '115.68.110.13'
production_project_root = '/var/zpanel/hostdata/dabory/public_html/wp-content/plugins/woosym-korean-localization'
production_user = 'dabory'

release_host = '115.68.110.13'
release_project_root = '/var/zpanel/hostdata/dabory/wskl/woosym-korean-localization'
release_user = 'dabory'

# AGS (올더게이트) 결제 모듈은 log 디렉토리를 만들고, 실행 권한을 달라고 함.
# 로그를 보내지 않도록 코드를 수정하기는 했지만, 혹시 모르므로 이렇게 처리함.
ags_log_path = 'includes/lib/homeags/log'

# KCP 결제 모듈은 binary 파일을 심어 두고 실행 권한을 달라고 함. 단, AGS 처럼 log 파일을
kcp_bin_path = 'includes/lib/homekcp/bin'
kcp_bin_targets = ('pp_cli', 'pp_cli_32', 'pp_cli_64', )


def check_env():
    if not env.hosts:
        print('Specify environment first!\ne.g)\n\t$ fab production deploy', file=sys.stderr)
        sys.exit(1)


@task
def test(branch='master'):
    env.host_name = 'Dabory'
    env.branch = branch
    env.hosts = test_host
    env.project_root = test_project_root
    env.user = test_user


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

    # KCP 결제 모듈 선처리: 바이너리 삭제
    # with cd(os.path.join(env.project_root, kcp_bin_path)):
    #     for t in kcp_bin_targets:
    #         run('rm %s' % t)

    with cd(env.project_root):
        with prefix('if [[ -n $SSH_ASKPASS ]]; then unset SSH_ASKPASS; fi'):
            run('git fetch')
            run('git checkout %s' % env.branch)
            run('git pull')

    # AGS 결제 모듈 후처리
    run('chmod 755 %s' % os.path.join(env.project_root, ags_log_path))

    # KCP 결제 모듈 후처리
    with cd(os.path.join(env.project_root, kcp_bin_path)):
        for t in kcp_bin_targets:
            run('chmod +x %s' % t)


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


@hosts([release_host, ])
@task
def release(branch='master'):
    env.host_name = 'Dabory'
    env.branch = branch
    env.project_root = release_project_root
    env.user = release_user

    print('Releasing woosym-korean-localization...')

    if not remote_exists(os.path.join(release_project_root, '.git')):
        print('.git not present! Cloning from git repository...')

        run('rm -rf "%s"' % env.project_root)
        path = os.path.dirname(env.project_root)
        clone_name = os.path.basename(env.project_root)

        # git clone
        with cd(path):
            with prefix('if [[ -n $SSH_ASKPASS ]]; then unset SSH_ASKPASS; fi'):
                run('git clone "%s" "%s"' % (git_url, clone_name, ))
                run('git checkout %s' % env.branch)
    else:
        with cd(env.project_root):
            with prefix('if [[ -n $SSH_ASKPASS ]]; then unset SSH_ASKPASS; fi'):
                run('git fetch')
                run('git checkout %s' % env.branch)
                run('git pull')

    # AGS 결제 모듈 후처리
    run('chmod 755 %s' % os.path.join(env.project_root, ags_log_path))

    # retrieve version
    with cd(env.project_root):
        out = run('grep \"define( \'WSKL_VERSION\', \" woosym-korean-localization.php')
        s = re.search(r'define\(\s*(\'|\")WSKL_VERSION(\'|\"),\s*\'(.+)\'\s*\);', out.stdout.strip())

        if s:
            version_info = s.groups()[2]
            print(green('Current branch\'s WSKL version: %s' % version_info))
        else:
            version_info = 'unversioned'
            print(red('Version information not found! Setting version name as %s' % version_info))

    # creating archive
    with cd(os.path.dirname(env.project_root)):
        output_file_gz = 'wskl-%s.tar.gz' % version_info
        output_file_zip = 'wskl-%s.zip' % version_info

        relative_dir = os.path.basename(env.project_root)
        latest_file_gz = 'latest.tar.gz'
        latest_file_zip = 'latest.zip'

        run('tar cpzf %s %s' % (output_file_gz, relative_dir))
        run('zip -r %s %s' % (output_file_zip, relative_dir))

        print(green('Do you want to make current output files be aliased as latest?'))
        q = raw_input('y/N ')

        if q.lower() == 'y':
            print(green('You have answered \'Yes\'. Creating soft symlink.'))
            run('rm -f %s' % latest_file_gz)
            run('rm -f %s' % latest_file_zip)
            run('ln -s %s %s' % (output_file_gz, latest_file_gz))
            run('ln -s %s %s' % (output_file_zip, latest_file_zip))
