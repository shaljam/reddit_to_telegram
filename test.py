import praw
from bot import send_to_telegram


def test_send_submission(submission_id):
    reddit = praw.Reddit(
        client_id='5HcYHPhZFHR14Q',
        client_secret='1RVyYaa-0it7zu2hCI2JVo80tuw',
        user_agent='telegram-poster',
    )

    submission = reddit.submission(id=submission_id)

    send_to_telegram(submission)


if __name__ == "__main__":
    test_send_submission('im5hbh')
