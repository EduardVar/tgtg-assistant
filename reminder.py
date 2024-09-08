from tgtg import TgtgClient
import tgtg_fuctions

from discord.ext import commands
import discord

class Reminder():
    store_name: str
    creator = None                  # Discord user's id
    initial_dic = None

    can_update = True
    expected_release = None         # None if not availible
    pickup_start = None
    pickup_end = None
    pre_notif_time = 5              # Time in minutes to notify before confirmed release date
    currently_released = False
    pre_release_notif = False
    release_notified = False
    
    ## Constructor
    def __init__(self, tgtg_client: TgtgClient, item_id: str, creator: discord.User):
        # Query item and test to confirm it's valid
        try: 
            temp_item = tgtg_client.get_item(item_id)   # If this passes, we know its valid

            self.initial_dic = temp_item
            self.creator = creator
            self.item_id = item_id
            self.store_name = temp_item["display_name"]
        except Exception as e:
            raise LookupError("The item you added was invalid - Exception: " + e) 
        
    # Get's the item dictionary using this reminder's item_id
    async def get_item(self, tgtg_client: TgtgClient) -> dict:
        return tgtg_fuctions.get_specific_item(tgtg_client, self.item_id)
    
    async def check_for_updates(self, item_dic: dict):

        # Keep setting new pickup interval
        temp_pickup_interval: dict = item_dic.get("pickup_interval")
        # That means the business does have a start and end time, set it
        if temp_pickup_interval is not None:
            self.pickup_start = temp_pickup_interval.get("start")
            self.pickup_end = temp_pickup_interval.get("end")

        # If past pickup_interval, you can now update the expected time 
        if self.expected_release is not None and self.expected_release <= await tgtg_fuctions.time_now_utc():
            # TODO: what happens when expected release is after pickup end?
            # TODO: what if sold out at the exact time it releases?
            self.can_update = True

        # Based on what time it sold out at
        sold_out_at = item_dic.get("sold_out_at")
        if sold_out_at is not None:
            self.currently_released = False

            # Reset notifs iff it's not within the pre-notif period
            if self.pre_notif_time < await tgtg_fuctions.time_diff_mins(self.expected_release):
                self.pre_release_notif = False
                self.release_notified = False

        # Only update expected_release if you can 
        if self.can_update:
            temp_next_window = item_dic.get("next_sales_window_purchase_start")

            # [Since it can only update during specific times] predict it based on when it was last sold out (if available)
            if sold_out_at is not None: # Since it got sold out, make currently released False
                self.expected_release = await tgtg_fuctions.tgtg_one_day_ahead(sold_out_at)
                self.can_update = False

            # Next, compare it based on when the next_sales_window_purchase_start is. Set the earlier time
            if temp_next_window is not None:
                # 1. If expected_release hasn't been set from the above sold_out_at time (is None)
                # OR 2. temp_next_window than the expected_release window
                if self.expected_release is None or temp_next_window < self.expected_release:
                    self.expected_release = temp_next_window
                    self.can_update = False


        '''FINAL CHECK/REMINDER'''
        # 1) AVAILABLE: pickup_interval, and NOT sold_out_at
        if not self.release_notified and self.pickup_start is not None and item_dic.get("sold_out_at") is None and not await self.is_unknown(item_dic):
            self.currently_released = True
            self.release_notified = True
            return tgtg_fuctions.PING_AVAILABLE
        
        # 2) PRERELEASE: pre_notif_time(min) <= (expected_release - time_now)
        elif not self.pre_release_notif and self.pre_notif_time >= await tgtg_fuctions.time_diff_mins(self.expected_release):
            self.pre_release_notif = True
            return tgtg_fuctions.PING_PRERELEASE
        
        else:
            return tgtg_fuctions.PING_NOTHING
        
    ###################################
    # HELPER FUNCTIONS
    ###################################
    async def get_initial(self):
        return self.initial_dic

    async def is_unknown(self, item_dic: dict):
        '''
        "check again later" or "nothing today" check
        '''
        if item_dic.get("item_tags") is not None:
            for tag in item_dic.get("item_tags"):
                long_text = tag.get("long_text").lower()

                if long_text == "check again later" or long_text == "nothing today":
                    return True

        # Didn't find any bad tags, return False that there is no unknown issues
        return False

    async def get_as_link(self):
        return f"<https://share.toogoodtogo.com/item/{self.item_id}/>"     
    
    async def get_str_preview(self):
        '''
        TGTG STORE (Surprise Bag) - AVAILABLE NOW (if applicable)
        Release expected at:  `[TIME] [TODAY/TOMORROW/TUES OCT 3] `
        Pickup at  `[TIME] : `[TIME] [TODAY/TOMORROW/TUES OCT 3]`
        '''
        expected = await tgtg_fuctions.time_diff_mins(self.expected_release)
        expected = expected if expected != tgtg_fuctions.UNKNOWN_MINS else "<???>"

        preview = f"**{self.store_name}** - {'CURRENTLY AVAILABLE' if self.currently_released else '`'+str(expected)+'` mins left.'}\n```\n"
        preview += f"Expected Release : {await tgtg_fuctions.easy_est(self.expected_release, short=True)}\n"
        preview += f"Pickup Time      : {await tgtg_fuctions.easy_est(self.pickup_start, short=True)} : {await tgtg_fuctions.easy_est(self.pickup_end, short=True)}\n```"

        return preview

    async def get_debug_preview(self):
        preview = f"**{self.store_name}** by {self.creator.mention}\n"
        preview += f"```\n==================================================\n"
        preview += f"can_update               = {self.can_update}\n"
        preview += f"expected_release         = {await tgtg_fuctions.easy_est(self.expected_release)}\n"
        preview += f"pickup_start:pickup_end  = {await tgtg_fuctions.easy_est(self.pickup_start)} : {await tgtg_fuctions.easy_est(self.pickup_end)}\n"
        preview += f"currently_released       = {self.currently_released}\n"
        preview += f"release_notified         = {self.release_notified}\n"
        preview += f"pre_release_notif        = {self.pre_release_notif}\n"
        preview += f"time remaining...        = {await tgtg_fuctions.time_diff_mins(self.expected_release)} mins\n```"

        return preview