#!/usr/bin/env python
""" update_apk_description.py

    Update the descriptions of an application (multilang)
"""
import sys
import os
import urllib2
import json

from oauth2client import client

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

# import the guts
from mozharness.base.script import BaseScript
from mozharness.mozilla.googleplay import GooglePlayMixin
from mozharness.base.python import VirtualenvMixin


class UpdateDescriptionAPK(BaseScript, GooglePlayMixin, VirtualenvMixin):
    all_actions = [
        'create-virtualenv',
        'update-apk-description',
        'test',
    ]

    default_actions = [
        'create-virtualenv',
        'test',
    ]

    config_options = [
        [["--service-account"], {
            "dest": "service_account",
            "help": "The service account email",
        }],
        [["--credentials"], {
            "dest": "google_play_credentials_file",
            "help": "The p12 authentication file",
            "default": "key.p12"
        }],
        [["--package-name"], {
            "dest": "package_name",
            "help": "The Google play name of the app",
        }],
        [["--l10n-api-url"], {
            "dest": "l10n_api_url",
            "help": "The L10N URL",
            "default": "https://l10n.mozilla-community.org/~pascalc/google_play_description/"
        }],

    ]

    # We have 3 apps. Make sure that their names are correct
    package_name_values = ("org.mozilla.fennec_aurora",
                           "org.mozilla.firefox_beta",
                           "org.mozilla.firefox")

    def __init__(self, require_config_file=False, config={},
                 all_actions=all_actions,
                 default_actions=default_actions):

        # Default configuration
        default_config = {
            'debug_build': False,
            'pip_index': True,
            # this will pip install it automajically when we call the
            # create-virtualenv action
            'virtualenv_modules': ['google-api-python-client'],
            "find_links": [
                "http://pypi.pvt.build.mozilla.org/pub",
                "http://pypi.pub.build.mozilla.org/pub",
            ],
            'virtualenv_path': 'venv',
        }
        default_config.update(config)

        BaseScript.__init__(
            self,
            config_options=self.config_options,
            require_config_file=require_config_file,
            config=default_config,
            all_actions=all_actions,
            default_actions=default_actions,
        )

        self.all_locales_url = self.config['l10n_api_url'] + "api/?done"
        self.locale_url = self.config['l10n_api_url'] + "api/?locale="
        self.mapping_url = self.config['l10n_api_url'] + "api/?locale_mapping&reverse"

    def check_argument(self):
        """ Check that the given values are correct,
        files exists, etc
        """
        if self.config['package_name'] not in self.package_name_values:
            self.fatal("Unknown package name value " +
                       self.config['package_name'])

        if not os.path.isfile(self.config['google_play_credentials_file']):
            self.fatal("Could not find " + self.config['google_play_credentials_file'])

    def get_list_locales(self):
        """ Get all the translated locales supported by Google play
        So, locale unsupported by Google play won't be downloaded
        Idem for not translated locale
        """
        response = urllib2.urlopen(self.all_locales_url)
        return json.load(response)

    def get_mapping(self):
        """ Download and load the locale mapping
        """
        response = urllib2.urlopen(self.mapping_url)
        self.mappings = json.load(response)

    def locale_mapping(self, locale):
        """ Google play and Mozilla don't have the exact locale code
        Translate them
        """
        if locale in self.mappings:
            return self.mappings[locale]
        else:
            return locale

    def update_desc(self, service, package_name):
        """ Update the desc on google play

        service -- The session to Google play
        package_name -- The name of the package
        locale -- The locale to update
        description -- The new description
        """

        edit_request = service.edits().insert(body={},
                                              packageName=package_name)
        result = edit_request.execute()
        edit_id = result['id']

        # Retrieve the mapping
        self.get_mapping()

        # Get all the locales from the web interface
        locales = self.get_list_locales()
        for locale in locales:
            response = urllib2.urlopen(self.locale_url + locale)

            description_json = json.load(response)
            title = description_json.get('title')
            shortDescription = description_json.get('short_desc')
            fullDescription = description_json.get('long_desc')

            # Google play expects some locales codes (de-DE instead of de)
            locale = self.locale_mapping(locale)

            try:
                self.log("Udating " + package_name + " for '" + locale +
                         "' /  desc (first chars): " + fullDescription[0:20])
                listing_response = service.edits().listings().update(
                    editId=edit_id, packageName=package_name, language=locale,
                    body={'fullDescription': fullDescription,
                          'shortDescription': shortDescription,
                          'title': title}).execute()

            except client.AccessTokenRefreshError:
                self.log('The credentials have been revoked or expired,'
                         'please re-run the application to re-authorize')

        # Commit our changes
        commit_request = service.edits().commit(
            editId=edit_id, packageName=package_name).execute()
        self.log('Edit "%s" has been committed' % (commit_request['id']))

    def update_apk_description(self):
        """ Update the description """
        self.check_argument()
        service = self.connect_to_play()
        self.update_desc(service, self.config['package_name'])

    def test(self):
        """ Test if the connexion can be done """
        self.check_argument()
        self.connect_to_play()

# main {{{1
if __name__ == '__main__':
    myScript = UpdateDescriptionAPK()
    myScript.run_and_exit()
