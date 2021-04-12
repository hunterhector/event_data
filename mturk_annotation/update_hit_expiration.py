import sys, os
import boto3
from typing import List, Tuple
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(".."))

from credentials import MTURK_ACCESS_KEY, MTURK_SECRET_KEY


def update_expiration_date(mturk_client, HITIds):
    for HITId, ext_days in HITIds:
        hit = mturk_client.get_hit(HITId=HITId)
        orig_expiry = hit["HIT"]["Expiration"]
        new_expiry = orig_expiry + timedelta(days=ext_days)
        mturk_client.update_expiration_for_hit(HITId=HITId, ExpireAt=new_expiry)

    return


if __name__ == "__main__":
    mturk_client = boto3.client(
        "mturk",
        aws_access_key_id=MTURK_ACCESS_KEY,
        aws_secret_access_key=MTURK_SECRET_KEY,
        region_name="us-east-1",
    )

    # HITs = [
    #     ("3XJOUITW91EWRS8OSO6HB0MAOLTQT1", 7),
    #     ("36D1BWBEIUOBMEGJHGF4T4TFE7K2MZ", 7),
    #     ("3N2YPY1GJDLM7HM8OSBWI1LH23LVEA", 7),
    #     ("3PGQRAZX1974LUMVUYILEHTQLBWSYH", 7),
    #     ("3WRBLBQ2HYV4YUHJRQDVXBG3LNNG0K", 7),
    #     ("3HXCEECSRTG1M689PQCTAAQT8QWZYT", 7),
    #     ("3S1L4CQSG4SUL7J688464WS4TWXFAD", 7),
    #     ("338431Z1GS2GQ1IG9M9IMGQSL1CROJ", 7),
    #     ("3K8CQCU3LLO3GCZQ71JBUQY4N6MWNC", 7),
    #     ("3IH9TRB0GIMI1A8WDXHYWSCT5UJI1J", 7),
    #     ("3A3KKYU7QA4XYUEQV04BHB94IGCMW2", 7),
    #     ("31MBOZ6PBVE4EEQ0EX3V54NCQV4CLH", 7),
    # ]
    HITs = [
        ("3MA5N0ATUJY286ENAORV2YH0TD1KWJ", 7),
        ("3E22YV8GH8TDW32PVF5G2WQ8UB3NPW", 7),
        ("3VZYA8PIUVL6IXSZAUU4TEPEVIS05D", 7),
        ("3HXCEECSRTG1M689PQCTAAQT8QWZYT", 7),
        ("3WRBLBQ2HYV4YUHJRQDVXBG3LNNG0K", 7),
        ("3PGQRAZX1974LUMVUYILEHTQLBWSYH", 7),
        ("3N2YPY1GJDLM7HM8OSBWI1LH23LVEA", 7),
        ("36D1BWBEIUOBMEGJHGF4T4TFE7K2MZ", 7),
        ("3XJOUITW91EWRS8OSO6HB0MAOLTQT1", 7),
    ]
    update_expiration_date(mturk_client, HITs)
