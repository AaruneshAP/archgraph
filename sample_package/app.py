"""
App module that imports base and utils and calls into them.
"""

import os
from base import BaseService
import utils


class AppService(BaseService):
    def run(self) -> str:
        msg = self.execute()
        formatted = utils.format_message("app", msg)
        total = utils.compute_total(10, 20)
        return f"{formatted} | Total: {total}"


def main() -> str:
    app = AppService("ProductionApp")
    return app.run()
