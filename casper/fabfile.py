# coding: utf-8

"""
일러두기
=======
* CASPER 용 *
* CASPER 용 *
* CASPER 용 *
* CASPER 용 *
* CASPER 용 *
* CASPER 용 *
* 아직 캐스퍼에서 검증되지 않았으므로 하지 말 것"

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
from fabric.colors import red, green

import json
import os
import sys

git_url = 'ssh://git@altssh.bitbucket.org:443/changwoo/casper.git'

production_host = '115.68.110.13'
# production_project_root = '/var/zpanel/hostdata/dabory/public_html/wp-content/plugins/casper'
production_project_root = '/var/zpanel/hostdata/dabory/casper-test'
production_user = 'dabory'
production_php = '/opt/php-5.6/bin/php'


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
    env.php = production_php


@task
def deploy():
    check_env()

    print(green('Deploying to server \'%s\'...' % env.host_name))

    with cd(env.project_root):
        with prefix('if [[ -n $SSH_ASKPASS ]]; then unset SSH_ASKPASS; fi'):
            run('git fetch')
            run('git checkout %s' % env.branch)
            run('git pull')

        run('php composer.phar dump-autoload --optimize')


@task
def reset():
    check_env()

    print(red('All files in the project root \'%s\'will be DESTROYED! Are you sure? ' % env.project_root))
    q = raw_input('Yes/no ')

    if q != 'Yes':
        print(green('The answer is not \'Yes\'. Stop resetting.'))
        sys.exit(0)

    run('rm -rf "%s"' % env.project_root)

    path = os.path.dirname(env.project_root)
    clone_name = os.path.basename(env.project_root)

    # git clone
    with cd(path):
        with prefix('if [[ -n $SSH_ASKPASS ]]; then unset SSH_ASKPASS; fi'):
            run('git clone "%s" "%s"' % (git_url, clone_name, ))

    # get composer
    with cd(env.project_root):
        run(env.php + ' -r \"readfile(\'https://getcomposer.org/installer\');\" > composer-setup.php')
        run(env.php + ' -r \"if (hash(\'SHA384\', file_get_contents(\'composer-setup.php\')) === \'781c98992e23d4a5ce559daf0170f8a9b3b91331ddc4a3fa9f7d42b6d981513cdc1411730112495fbf9d59cffbf20fb2\') { echo \'Installer verified\'; } else { echo \'Installer corrupt\'; unlink(\'composer-setup.php\'); }\"')
        run(env.php + ' -d suhosin.executor.include.whitelist=phar composer-setup.php')
        run(env.php + ' -r "unlink(\'composer-setup.php\');"')
        run('chmod +x composer.phar')


@hosts(['localhost:2222', ])
@task
def local_testing():
    """
    vagrant 접속해서 scratch 부터 dabory 를 설정해 올바르게 프로그램이 동작하는지 검사

    노트.
    1. /etc/bash.bashrc 파일에 다음과 같이 앨리어싱한다.

     # Load xdebug Zend extension with php command
     alias php='php -dzend_extension=xdebug.so'

     # PHPUnit needs xdebug for coverage. In this case, just make an alias with php command prefix.
     alias phpunit='php $(which phpunit)'

    2. 웹브라우저가 올바르게 URL을 통해 접속 가능한지 먼저 확인
    3. wp environment file 확인
        e.g)
        ~/testing$ cat wp-cli.local.yml
        path: casper-testing
        url: http://casper-testing.local
    """
    env.user = 'vagrant'
    env.password = 'vagrant'
    env.php = '/usr/bin/php'

    env.wp_root = '/home/vagrant/testing/casper-testing'
    env.wp_locale = 'ko_KR'

    env.wp_admin_user = 'changwoo'
    env.wp_admin_pass = '0000'
    env.wp_admin_email = 'ep6tri@hotmail.com'

    env.wp_db_name = 'casper-testing'
    env.wp_db_user = 'casper-testing'
    env.wp_db_pass = 'casper-testing'

    env.wp_url = 'http://casper-testing.local:8080'

    extra_script = """<<PHP
define( 'WP_DEBUG', true );
define( 'WP_DEBUG_LOG', true );
define( 'WP_DEBUG_LOG_DISPLAY', false );
define( 'WSKL_DEBUG', true );
PHP"""

    title = 'CASPER-TESTING'

    # reset phase: 워드프레스와 데이터베이스를 초기화
    with cd(os.path.dirname(env.wp_root)):
        run('wp db reset --yes')
        run('rm -rf %s' % env.wp_root)
        run('mkdir %s' % env.wp_root)

    # install phase: 워드프레스 설치, 설정
    with cd(env.wp_root):
        # 다운로드
        run('wp core download --path=%s --locale=%s --force' % (env.wp_root, env.wp_locale))

        # 설정 파일 생성
        run('wp core config --url=%s --dbname=%s --dbuser=%s --dbpass=%s --extra-php %s'
            % (env.wp_url, env.wp_db_name, env.wp_db_user, env.wp_db_pass, extra_script))

        # 설정대로 DB에 워드프레스 설치
        run('wp core install --url=%s --title=%s --admin_user=%s --admin_password=%s --admin_email=%s --skip-email'
            % (env.wp_url, title, env.wp_admin_user, env.wp_admin_pass, env.wp_admin_email))

        # 우커머스 다운로드
        run('wp plugin install woocommerce')

        # 우커머스 활성화
        run('wp plugin activate woocommerce')

    # 캐스퍼 클론
    with cd(os.path.join(env.wp_root, 'wp-content', 'plugins')):
        run('git clone "%s"' % (git_url, ))

    # 캐스퍼 초기화
    with cd(os.path.join(env.wp_root, 'wp-content', 'plugins', 'casper')):
        run(env.php + ' -r \"readfile(\'https://getcomposer.org/installer\');\" > composer-setup.php')
        run(env.php + ' -d suhosin.executor.include.whitelist=phar composer-setup.php')
        run(env.php + ' -r "unlink(\'composer-setup.php\');"')
        run('chmod +x composer.phar')
        run('./composer.phar update')
        run('./composer.phar dump-autoload --optimize')

    # 캐스퍼 활성화
    with cd(env.wp_root):
        run('wp plugin activate casper')
