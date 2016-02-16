#!/bin/bash

. ${BASH_SOURCE%/*}/common.sh

function get_web_service
{
    which apache2 &>/dev/null && {
        echo -e "apache2"
        return
    } || :

    which httpd &>/dev/null && {
        echo -e "httpd"
        return
    } || :

    which nginx &>/dev/null && {
        echo -e "nginx"
        return
    } || :
}

function get_user_web_service
{
    echo -n $(ps axho user,comm | grep -E $(get_web_service) | uniq | grep -v "root" | cut -d " " -f 1 | uniq)
}

function get_apache_name()
{
    if which apache2 1>/dev/null 2>/dev/null
    then
        echo "apache2"
    elif which httpd 1>/dev/null 2>/dev/null
    then
        echo "httpd"
    else
        echo ""
    fi
}

function get_apache_version()
{
    _NAME=$(get_apache_name)
    if [ -n "$_NAME" ]
    then
        echo -n $($_NAME -v | grep '^Server version' | cut -d ' ' -f 3 | cut -d '/' -f 2)
    else
        echo ""
    fi
}

function get_config_path()
{
    if [ -d "/etc/apache/conf.d" ]
    then
        echo "/etc/apache/conf.d"
    elif [ -d "/etc/apache2/conf.d" ]
    then
        echo "/etc/apache2/conf.d"
    elif [ -d "/etc/httpd/conf.d" ]
    then
        echo "/etc/httpd/conf.d"
    elif [ -d "/etc/apache2/sites-enabled" ]
    then
        echo "/etc/apache2/sites-enabled"
    else
        echo ""
    fi
}

function create_apache_config()
{
    _CONF_PATH=$(get_config_path)
    if [ -z "$_CONF_PATH" ]
    then
        echo "Apache path not found."
        exit 1
    fi

    _ALLOW_ALL="Require all granted"
    _ALLOW_FROM="Require host 127.0.0.1"
    version_gt "2.3" $(get_apache_version) && {
        _ALLOW_ALL="Order allow,deny
    Allow from all"
        _ALLOW_FROM="Order deny,allow
    Deny from all
    Allow from 127.0.0.1"
    } || :

    _STATIC_ROOT=$(get_migasfree_setting STATIC_ROOT)
    _MIGASFREE_REPO_DIR=$(get_migasfree_setting MIGASFREE_REPO_DIR)
    _MIGASFREE_APP_DIR=$(get_migasfree_setting MIGASFREE_APP_DIR)

    _CONF_FILE=$_CONF_PATH/migasfree.conf
    cat > $_CONF_FILE << EOF
Alias /static $_STATIC_ROOT
<Directory $_STATIC_ROOT>
    $_ALLOW_ALL
    Options Indexes FollowSymlinks
    IndexOptions FancyIndexing
</Directory>

Alias /repo $_MIGASFREE_REPO_DIR
<Directory $_MIGASFREE_REPO_DIR>
    $_ALLOW_ALL
    Options Indexes FollowSymlinks
    IndexOptions FancyIndexing
</Directory>

<Directory $_MIGASFREE_REPO_DIR/errors>
    $_ALLOW_FROM
    Options Indexes FollowSymlinks
    IndexOptions FancyIndexing
</Directory>

WSGIScriptAlias / $_MIGASFREE_APP_DIR/wsgi.py
<Directory $_MIGASFREE_APP_DIR>
    <Files wsgi.py>
        $_ALLOW_ALL
    </Files>
</Directory>
EOF
}

function set_web_server_permissions()
{
    _USER=$(get_user_web_service)
    # owner for repositories
    _REPO_PATH=$(get_migasfree_setting MIGASFREE_REPO_DIR)
    owner $_REPO_PATH $_USER

    # owner for keys
    _KEYS_PATH=$(get_migasfree_setting MIGASFREE_KEYS_DIR)
    owner $_KEYS_PATH $_USER
    chmod 700 $_KEYS_PATH

    # owner for migasfree.log
    _TMP_DIR=$(get_migasfree_setting MIGASFREE_TMP_DIR)
    touch "$_TMP_DIR/migasfree.log"
    owner "$_TMP_DIR/migasfree.log" $_USER
}

function web_server_init()
{
    export DJANGO_SETTINGS_MODULE="migasfree.settings.production"
    django-admin.py collectstatic --noinput

    service_action haveged start

    create_apache_config
    boot_at_start $(get_apache_name)
    service_action $(get_apache_name) start

    python -c "import django; django.setup(); from migasfree.server.security import create_keys_server; create_keys_server()"
    set_web_server_permissions
}
