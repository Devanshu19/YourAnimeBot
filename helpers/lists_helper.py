import requests
from discord import Embed, Member

from views.scroller import Scroller
from managers import mongo_manager
from helpers import general_helper
from queries import fav_queries
import config

all_lists = ["ptw", "ptr", "planning", "crt", "current", "watching", "wtc", "reading", "comp", "completed", "drp", "dropped", "fav", "favorite"]

lists = {
    "ptw" : "PLANNING",
    "ptr" : "PLANNING",
    "planning" : "PLANNING",
    "crt" : "CURRENT",
    "current" : "CURRENT",
    "wtc" : "CURRENT",
    "watching" : "CURRENT",
    "reading" : "CURRENT",
    "comp" : "COMPLETED",
    "completed" : "COMPLETED",
    "drp" : "DROPPED",
    "dropped" : "DROPPED",
    "fav" : "FAVOURITE",
    "favorite" : "FAVOURITE"
}

"""Adds specified anime to the specified list"""

async def add_to_list(list_name:str, mediaID:int, user:Member, media_type:str="ANIME") -> Embed:

    lst = lists[list_name]

    if lst == "FAVOURITE":
        return await add_to_fav(mediaID, user, media_type)

    list_query = """
        mutation($id:Int!, $list:MediaListStatus){
            SaveMediaListEntry(mediaId:$id, status:$list){
                id 
                status
            }
        }
    """

    token = (await mongo_manager.manager.get_user(str(user.id)))["token"]

    list_resp = requests.post(
        url=config.ANILIST_BASE,
        json={
            "query" : list_query,
            "variables" : {
                "id" : mediaID,
                "list" : lst
            }
        },
        headers={
            "Authorization" : token
        }
    ).json()    
    
    if list_resp["data"]["SaveMediaListEntry"] is None:
        return await general_helper.get_information_embed(
            title="Whoops",
            description="The following error occurred : ```{}```".format(list_resp["error"]["message"]),
            color=config.ERROR_COLOR
        )

    return await general_helper.get_information_embed(
        title="Done",
        description="{} was added to your `{}` list.".format(media_type, lst)
    )

async def add_to_fav(mediaID:int, user:Member, media_type:str="ANIME"):

    data = await mongo_manager.manager.get_user(str(user.id))

    if media_type == "ANIME":
        fav_query = fav_queries.anime_query
    elif media_type == "MANGA":
        fav_query = fav_queries.manga_query
    elif media_type == "CHARACTER":
        fav_query = fav_queries.character_query

    resp = requests.post(
        url=config.ANILIST_BASE,
        json={
            "query" : fav_query,
            "variables" : {
                "id" : mediaID
            }
        },
        headers={
            "Authorization" : data["token"]
        }
    ).json()

    fav_data = resp["data"]

    if fav_data is None:
        return await general_helper.get_information_embed(
            title="Whoops!",
            description="The following error(s) occurred : ```{}```".format("\n".join([error["message"] for error in resp["errors"]])),
            color=config.ERROR_COLOR
        )

    return await general_helper.get_information_embed(
        title="Done",
        description="That {} was added to your favourite. ".format(media_type)
    )

async def get_list_paginator(target:Member, list_name:str):

    anilistID = await general_helper.get_id_from_userID(str(target.id))

    list_query = """
        query($id:Int!, $status:MediaListStatus){
            MediaListCollection(userId:$id, type:ANIME, status:$status, sort:UPDATED_TIME_DESC){
                lists{
                    name
                    entries{
                        media{
                            title{
                                english
                                romaji
                            }
                            siteUrl
                            episodes
                        }
                        progress
                    }
                    isCustomList
                }
            }
        }
    """

    list_resp = requests.post(
        url=config.ANILIST_BASE,
        json={
            "query" : list_query,
            "variables" : {
                "id" : anilistID,
                "status" : list_name
            }
        }
    ).json()

    list_data = None

    for i in list_resp["data"]["MediaListCollection"]["lists"]:
        if i["isCustomList"] is False:
            list_data = i

    if list_data is None:
        return None

    entries = list_data["entries"]
    entries_size = len(entries)

    pages = []

    MAX_LISTINGS_PER_PAGE = 10
    current_listing_count = 0

    current_embed = Embed(
        title=list_data["name"] + " list",
        description="Total : {}\n\n".format(len(entries))
    )
    
    for i in range(entries_size):

        current_listing_count += 1

        if current_listing_count > MAX_LISTINGS_PER_PAGE:
            current_listing_count = 1
            pages.append(current_embed)
            current_embed = Embed(
                title=list_data["name"] + " list",
                description="Total : {}\n\n".format(entries_size)
            )

        current_title = (entries[i]["media"]["title"]["english"] if entries[i]["media"]["title"]["english"] is not None else entries[i]["media"]["title"]["romaji"])
        current_embed.description += "{bullet} [{name}]({url}) {progress}/{episodes}\n".format(
            bullet=config.BULLET_EMOTE,
            name=current_title,
            url=entries[i]["media"]["siteUrl"],
            progress=entries[i]["progress"],
            episodes=entries[i]["media"]["episodes"]
        )

        if i >= entries_size - 1:
            pages.append(current_embed)

    if len(pages) > 0:
        return Scroller(pages, True)
    else:
        return None

async def get_fav_paginator(target:Member, fav_type:str) -> Scroller:

    if fav_type == "ANIME":
        fav_query = fav_queries.anime_list_query
    elif fav_type == "MANGA":
        fav_query = fav_queries.manga_list_query

    anilistID = await general_helper.get_id_from_userID(str(target.id))

    resp = requests.post(
        url=config.ANILIST_BASE,
        json={
            "query" : fav_query,
            "variables" : {
                "userID" : anilistID
            }
        }
    ).json()

    entries = resp["data"]["User"]["favourites"]["{}".format(fav_type.lower())]["nodes"] # List of media elements
    entries_size = len(entries)

    MAX_ENTRIES_PER_PAGE = 10
    current_entries_count = 0

    pages = []

    current_embd = Embed(
        title="Favourite {}".format(fav_type.capitalize()),
        description="Total : {} \n\n".format(len(entries))
    )

    for i in range(entries_size):

        current_entries_count += 1

        if current_entries_count > MAX_ENTRIES_PER_PAGE:
            pages.append(current_embd)
            current_embd = Embed(
                title="Favourite {}".format(fav_type.capitalize()),
                description="Total : {} \n\n".format(entries_size)
            )

        title = (entries[i]["title"]["english"] if entries[i]["title"]["english"] is not None else entries[i]["title"]["romaji"])
        current_embd.description += "{bullet} [{name}]({url}) \n".format(bullet=config.BULLET_EMOTE, name=title, url=entries[i]["siteUrl"])

        if i >= entries_size - 1:
            pages.append(current_embd)

    if len(pages) > 0:
        return Scroller(pages, show_all_btns=True)
    else:
        return None

    
