# -*- coding: utf-8 -*-

import os
import json
import gpgme

from io import BytesIO

from django.conf import settings

from . import errmfs
from .functions import readfile, writefile

SIGN_LEN = 256


def sign(filename):
    os.system("openssl dgst -sha1 -sign %s -out %s %s" % (
        os.path.join(settings.MIGASFREE_KEYS_DIR, 'migasfree-server.pri'),
        "%s.sign" % filename,
        filename
    ))


def verify(filename, key):
    return os.system(
        "openssl dgst -sha1 -verify %s -signature %s %s 1>/dev/null" %
        (
            os.path.join(settings.MIGASFREE_KEYS_DIR, '%s.pub' % key),
            "%s.sign" % filename,
            filename
        )
    ) == 0  # returns True if OK, False otherwise


def check_keys_path():
    if not os.path.lexists(settings.MIGASFREE_KEYS_DIR):
        os.makedirs(settings.MIGASFREE_KEYS_DIR)


def gen_keys(name):
    """
    Generates a pair of RSA keys
    """
    check_keys_path()

    private_key = os.path.join(settings.MIGASFREE_KEYS_DIR, "%s.pri" % name)
    public_key = os.path.join(settings.MIGASFREE_KEYS_DIR, "%s.pub" % name)

    if not (os.path.exists(private_key) and os.path.exists(public_key)):
        os.system("openssl genrsa -out %s 2048" % private_key)
        os.system("openssl rsa -in %s -pubout > %s" % (private_key, public_key))

        # read only keys
        os.chmod(private_key, 0o400)
        os.chmod(public_key, 0o400)


def gpg_get_key(name):
    """
    Return keys gpg and if not exists it is created
    """

    gpg_home = os.path.join(settings.MIGASFREE_KEYS_DIR, '.gnupg')
    gpg_conf = os.path.join(gpg_home, 'gpg.conf')
    _file = os.path.join(gpg_home, '{}.gpg'.format(name))

    if not os.path.exists(_file):
        os.environ['GNUPGHOME'] = gpg_home
        if not os.path.exists(gpg_home):
            os.makedirs(gpg_home, 0o700)
            # create a blank configuration file
            with open(gpg_conf, 'wb') as handle:
                handle.write('cert-digest-algo SHA256\ndigest-algo SHA256')

            os.chmod(gpg_conf, 0o600)

        _file_params = os.path.join(gpg_home, '%s.txt' % name)
        with open(_file_params, 'wb') as handle:
            key_params = """
Key-Type: RSA
Key-Length: 4096
Name-Real: %s
Name-Email: fun.with@migasfree.org
Expire-Date: 0
"""
            handle.write(key_params % name)

        os.system(
            "echo '' | $(which gpg) --batch "
            "--passphrase-fd 0 --gen-key %(file)s; rm %(file)s" % {
                "file": _file_params
            }
        )

        # export and save
        ctx = gpgme.Context()
        ctx.armor = True
        keydata = BytesIO()
        ctx.export(name, keydata)
        _key = keydata.getvalue()
        with open(_file, 'wb') as handle:
            handle.write(_key)

        os.chmod(_file, 0o600)

    with open(_file, 'rb') as handle:
        _key = handle.read()

    return _key


def get_keys_to_client(project):
    """
    Returns the keys for register computer
    """
    if not os.path.exists(
        os.path.join(settings.MIGASFREE_KEYS_DIR, "{}.pri".format(project))
    ):
        gen_keys(project)

    server_public_key = readfile(os.path.join(
        settings.MIGASFREE_KEYS_DIR,
        "migasfree-server.pub"
    ))
    project_private_key = readfile(os.path.join(
        settings.MIGASFREE_KEYS_DIR,
        "{}.pri".format(project)
    ))

    return {
        "migasfree-server.pub": server_public_key,
        "migasfree-client.pri": project_private_key
    }


def get_keys_to_packager():
    """
    Returns the keys for register packager
    """
    server_public_key = readfile(os.path.join(
        settings.MIGASFREE_KEYS_DIR,
        "migasfree-server.pub"
    ))
    packager_private_key = readfile(
        os.path.join(settings.MIGASFREE_KEYS_DIR, "migasfree-packager.pri")
    )

    return {
        "migasfree-server.pub": server_public_key,
        "migasfree-packager.pri": packager_private_key
    }


def create_keys_server():
    gen_keys("migasfree-server")
    gen_keys("migasfree-packager")
    gpg_get_key("migasfree-repository")


def wrap(filename, data):
    """
    Creates a signed wrapper file around data
    """
    with open(filename, 'wb') as fp:
        json.dump(data, fp)

    sign(filename)

    with open(filename, 'ab') as fp:
        with open("{}.sign".format(filename), "rb") as fpsign:
            fp.write(fpsign.read())

    os.remove("{}.sign".format(filename))


def unwrap(filename, key):
    """
    Returns data inside signed wrapper file
    """
    with open(filename, 'rb') as fp:
        content = fp.read()

    n = len(content)

    writefile("{}.sign".format(filename), content[n - SIGN_LEN:n])
    writefile(filename, content[0:n - SIGN_LEN])

    if verify(filename, key):
        with open(filename, "rb") as f:
            data = json.load(f)
    else:
        data = errmfs.error(errmfs.INVALID_SIGNATURE)

    os.remove("{}.sign".format(filename))

    return data
