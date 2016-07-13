import requests
import json


def build_slack_attachment(fallback, pretext, text, level, title, fields, thumb_url, markdown_in):
    attachment = {'fallback': fallback,
                  'pretext': pretext,
                  'color': level,
                  'text': text,
                  'title': title,
                  'fields': fields,
                  'thumb_url': thumb_url,
                  'mrkdwn_in': markdown_in}
    return attachment


def build_slack_field(title, message):
    field = {'title': title,
             'value': message,
             'short': False}
    return field


def build_slack_payload(attachments, message_text, username, emoji, channel):
    payload = {'attachments': attachments,
               'text': message_text,
               'username': username,
               'icon_emoji': str(":" + emoji + ":"),
               'channel': channel}
    return json.dumps(payload)


def send_slack_webhook(api_url, slack_payload):
    """
    :param api_url: slack API url provided by incoming webhook integration
    :param slack_payload: message payload to be sent to slack channel
    Send message to a specified slack channel
    """
    response = requests.post(api_url, slack_payload)

    if response.content == b'ok':
        # log.info("Message posted (content: {})".format(slack_payload))
        return True
    else:
        # log.critical("Slack response {}".format(response.status_code))
        return False
