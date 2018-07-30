from time import sleep

import web

from bathroomavailable import BathroomAvailable


def main():
    bathroom_available = BathroomAvailable()

    try:
        if bathroom_available.is_master:
            urls = (
                '/GetBathroomStatus', 'bathroomavailable.GetBathroomStatus',
                '/UpdateBathroomStatus', 'bathroomavailable.UpdateBathroomStatus',
            )
            web.config.update({'bathroom_available': bathroom_available})
            web_app = web.application(urls, globals())
            web_app.run()
        else:
            while True:
                sleep(60)
    finally:
        bathroom_available.cleanup()


if __name__ == '__main__':
    main()
