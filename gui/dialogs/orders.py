from collections import defaultdict
import re
from rich import print

from PyQt6.QtWidgets import QDialog, QWidget
from PyQt6.uic.load_ui import loadUi

from msc.es2.types import ES2Field


class OrderDialog(QDialog):
    data: dict[str, ES2Field]

    def __init__(self, data: dict[str, ES2Field], parent: QWidget):
        super().__init__(parent)
        self.data = data

        re_ads = re.compile(r"^List(?P<id>(Pic|Rand|Reg)(\d+))(?P<key>\S+)$")
        re_mail = re.compile(r"^OrderYP(?P<id>\d+)(?P<wait>ID2)?$")

        ads = defaultdict(dict)
        mail_orders = defaultdict(dict)

        for tag in sorted(data.keys()):
            if tag.startswith("List"):
                m = re_ads.match(tag)
                if m:
                    ads[m.group("id")][m.group("key")] = data[tag].value
                ...
            elif tag.startswith("OrderYP"):
                if tag == "OrderYP":# order counter
                    continue
                m = re_mail.match(tag)
                if m:
                    id = m.group("id")
                    if m.group("wait"):
                        mail_orders[id]["wait"] = data[tag].value
                    else:
                        mail_orders[id]["data"] = data[tag].value
                else:
                    print("No match:", tag)
        print(ads)
        print(mail_orders)
        self.close()
