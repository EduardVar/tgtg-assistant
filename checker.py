import discord
from discord.ext import tasks, commands
from tgtg import TgtgClient

from typing import List
import asyncio, random, traceback

from reminder import Reminder
import tgtg_fuctions

class CheckerCog(commands.Cog):
    bot = commands.Bot
    tgtg_client = TgtgClient

    # All in seconds
    reminders: List[Reminder]
    loop_time = 60      # Future - wait additional time on top of loop time?
    #additional_sleep = 60
    low_end_check = 7.5
    high_end_check = loop_time
    
    ###################################
    # TASK FUNCTIONS
    def __init__(self, bot: commands.Bot, tgtg_client: TgtgClient, ann_chann: discord.TextChannel):
        self.bot = bot
        self.tgtg_client = tgtg_client
        self.ann_chann = ann_chann
        self.reminders = []

        print("Waiting for top of the minute...")
        while tgtg_fuctions.is_top_of_min() is False:
            #print("Waiting for top of the minute...")
            pass

        print("Starting loop @ top of the minute.")
        self.task_check_assigned.start()

    def task_end(self):
        self.task_check_assigned.cancel()

    @tasks.loop(seconds=loop_time)
    async def task_check_assigned(self):
        try:
            #await self.bot.wait_until_ready()

            # 1. Use list given in instantiation/update function to know what to look for
            print("Reminders:", self.reminders)

            # 2. Between low-high seconds, query the item, get time/availibility
            for rem in self.reminders:
                item = await rem.get_item(self.tgtg_client)

                ping_code = -1
                try:
                    # Update reminder, get output from it. If it's not None, ping creator
                    ping_code = await rem.check_for_updates(item)
                    print(ping_code,":",rem.store_name)
                except:
                    print(traceback.format_exc())
                    await self.ping_user(rem, "Exception occured: check console for details.")

                # Notify user
                if ping_code is tgtg_fuctions.PING_AVAILABLE:
                    await self.ping_user(rem, f"**{rem.store_name}** is ***AVAILABLE NOW!***: {await rem.get_as_link()}") 
                elif ping_code is tgtg_fuctions.PING_PRERELEASE:
                    await self.ping_user(rem, f"**{rem.store_name}** available in **{rem.pre_notif_time} minutes** at **{await tgtg_fuctions.easy_est(rem.expected_release, True)}**.")
                elif ping_code is tgtg_fuctions.PING_ERROR:
                    await self.ann_chann.send(f"`Exception occurred when checking ping for item {rem.store_name}`")

                # Wait a random time to not overwhelm api
                await asyncio.sleep(random.uniform(self.low_end_check, self.high_end_check))
        except Exception as e:
            print("During automatic round checking, an exception occured...")
            print(traceback.format_exc())
            await self.ann_chann.send("`Task ended due to exception.`")
            await self.ann_chann.send("```\n" + traceback.format_exc() + "\n```")
            self.task_end()


    ###################################
    # USER FUNCTIONS
    async def add_reminder(self, tgtg_client: TgtgClient, user: discord.User, arg: str) -> str:
        if await self.valid_to_add() is not True:
            return "Failed - Too many reminders. Please delete some."

        try: 
            # Parse item_id out of the url. Ex: https://share.toogoodtogo.com/item/123456/
            item_id = arg.split("/")[-2]

            # Create reminder (this also verifies it)
            new_reminder = Reminder(tgtg_client, item_id, user)

            for rem in self.reminders:
                if new_reminder.store_name == rem.store_name and new_reminder.creator == rem.creator:
                    return "Failed - This item is a duplicate..."

            # If it was successfully created, add to the list checker would be analyzing
            self.reminders.append(new_reminder)

            # Wait after adding to not overwhelm API
            await asyncio.sleep(random.uniform(self.low_end_check, self.low_end_check+0.1))

            return f"Sucess - **{new_reminder.store_name}** has been added!"
        except Exception as e:
            print(traceback.format_exc())
            return "Failed - The item you tried to add was invalid... (Could also be 403 error)"
        
    async def remove_reminder(self, user: discord.User, arg: str) -> str:
        try:
            index = int(arg)    # Try to convert what user provided in message
        except:
            return "Failed - Incorrect index formatting..."
        
        try:
            rem = await self.get_rem_from_index(user, index)
            self.reminders.remove(rem)
            return f"Sucessfully deleted **{rem.store_name}**."
        except:
            print(traceback.format_exc())
            return "Failed - Was not able to delete sucessfully..."

    async def remove_all_user_rems(self, user: discord.User) -> str:
        try:
            for rem in await self.get_user_reminders(user):
                self.reminders.remove(rem)

            return f"Sucess - deleted all reminders for user {user.mention}"
        except:
            print(traceback.format_exc())
            return "Failed - deleting all of this user's reminders..."

    async def get_rem_info_idx(self, user: discord.User, arg: str) -> str:
        try:
            index = int(arg)    # Try to convert what user provided in message
        except:
            return "Failed - Incorrect index formatting...?"
        
        try:
            rem = await self.get_rem_from_index(user, index)
            return await rem.get_str_preview()
        except:
            print(traceback.format_exc())
            return "Failed - Was not able to retrieve info sucessfully... wrong index?"
        
    async def get_rem_info_url(self, tgtg_client: TgtgClient, user: discord.User, arg: str) -> str:
        try: 
            # Parse item_id out of the url. Ex: https://share.toogoodtogo.com/item/123456/
            item_id = arg.split("/")[-2]

            # Create reminder (this also verifies it)
            tmp_rem = Reminder(tgtg_client, item_id, user)
            await tmp_rem.check_for_updates(await tmp_rem.get_initial())

            return await tmp_rem.get_str_preview()
        except Exception as e:
            print(traceback.format_exc())
            return "Failed - Make sure its the correct url format for check."
        
    async def get_rem_debug(self, user: discord.User, arg: str) -> str:
        try:
            index = int(arg)    # Try to convert what user provided in message
        except:
            return "Failed - Incorrect index formatting...?"
        
        try:
            rem = await self.get_rem_from_index(user, index)
            return await rem.get_debug_preview()
        except:
            print(traceback.format_exc())
            return "Failed - Was not able to retrieve info sucessfully... wrong index?"
        
    async def get_repostable_for_user(self, user: discord.User):
        user_rems = await self.get_user_reminders(user)
        csv_content = ""
        for rem in user_rems:
            csv_content += await rem.get_as_link() + ","

        return "" if csv_content == "" else f"{user.mention}\n!add {csv_content[:-1]}"

    ###################################
    # HELPER FUNCTIONS
    async def valid_to_add(self) -> bool:
        # Calculate new high value for random checking and makes sure it doesn't break anything
        # Time between checks is > low value and < high value
        new_high = self.loop_time // (len(self.reminders) + 1)
        if new_high < self.low_end_check:
            return False
        else:
            self.high_end_check = new_high  # Set it if valid
            return True
    
    async def get_user_reminders(self, user: discord.User) -> List[Reminder]:
        return [rem for rem in self.reminders if rem.creator == user]

    async def get_user_with_time_rems(self, user: discord.User) -> List[str]:
        formatted = []
        for user_rem in await self.get_user_reminders(user):
            if user_rem.currently_released:
                formatted.append( "**AVAILABLE**: "+user_rem.store_name )
            else:
                formatted.append( "**"+(await tgtg_fuctions.easy_est(user_rem.expected_release, short=True) if user_rem.expected_release != None else "N/A")+"**: "+user_rem.store_name )

        return formatted

    async def get_rem_from_index(self, user: discord.User, index: int) -> Reminder:
        i = 1
        for rem in self.reminders:
            # Delete if this is the index the user specified
            if rem.creator == user:
                if i == index:
                    return rem
                else:
                    i += 1  # Increase i by 1 it's still the right user
        return None     # If couldn't find it, return `None``

    async def ping_user(self, rem: Reminder, message: str):
        await self.ann_chann.send(rem.creator.mention + " " + message)

    async def check_login_token(self) -> str:
        try:
            self.tgtg_client.login()
            return "Success - logged in."
        except:
            return "Failed - 403 error."
