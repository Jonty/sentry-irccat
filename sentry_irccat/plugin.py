import socket

from django import forms
from sentry.conf import settings
from sentry.plugins import Plugin
from sentry.plugins.bases.notify import NotificationConfigurationForm
import sentry_irccat


class IRCCatConfigurationForm(NotificationConfigurationForm):
    host = forms.CharField(label='Host', required=False, help_text='irccat host')
    port = forms.IntegerField(label='Port', required=False, help_text='irccat port')
    rules = forms.CharField(label='Rules', required=False, help_text='Format: numeric_loglevel = #channelname. One per line, * matches all log levels.', widget=forms.Textarea)


class IRCCatMessage(Plugin):
    title = 'IRCCat-Multi'
    conf_key = 'irccat_multi'
    slug = 'irccat_multi'
    version = sentry_irccat.VERSION
    author = 'Russ Garrett / Jonty Wareing'
    author_url = 'http://www.github.com/jonty/sentry-irccat'
    project_conf_form = IRCCatConfigurationForm

    def is_configured(self, project):
        return all(self.get_option(k, project) for k in ('host', 'port', 'rules'))

    def post_process(self, group, event, is_new, is_sample, **kwargs):
        if not is_new or not self.is_configured(event.project):
            return

        link = '%s/%s/group/%d/' % (settings.URL_PREFIX, group.project.slug,
                                    group.id)
        message = '[sentry %s] %s: %s' % (event.server_name, link, event.message)

        self.send_payload(event.project, event.level, message)

    def send_payload(self, project, message_level, message):
        rules = self.get_option('rules', project).splitlines()
        for rule in rules:
            level, channel = rule.split('=')
            level = level.strip()
            channel = channel.strip()

            if not level and not channel:
                print "Invalid rule '%s', skipping" % rule
                continue

            if str(message_level) == level or level == '*':

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.get_option('host', project), self.get_option('port', project)))
                msg = "%s %s\r\n" % (channel, message)
                sock.send(msg)
                sock.close()
