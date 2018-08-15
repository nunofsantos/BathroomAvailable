from time import sleep

import web

from bathroomavailable import BathroomAvailable


def main():
    bathroom_available = None
    try:
        bathroom_available = BathroomAvailable()

        if bathroom_available.device_type == bathroom_available.MASTER:
            urls = (
                '/GetBathroomStatus', 'bathroomavailable.GetBathroomStatus',
                '/UpdateBathroomStatus', 'bathroomavailable.UpdateBathroomStatus',
            )
            web.config.update({'bathroom_available': bathroom_available})
            web_app = web.application(urls, globals())
            web_app.run()
        else:
            # SLAVE or SOLO
            while True:
                sleep(60)
    finally:
        if bathroom_available:
            bathroom_available.cleanup()


if __name__ == '__main__':
    main()
