from discord import Embed, Member
from discord.ext import commands
from datetime import datetime
import requests
import jwt

from views.select_view import SelectPaginator
from managers import mongo_manager
from helpers import general_helper
import config

"""Just a way to transmit paginator and ids at the same time. Please no bully"""

class MediaData:
    media_id:int = None
    media_type = None
    titles:list = None
    genre:list = None
    url:str = None

    def __init__(self, media_id:int, media_type:str="ANIME", title:list=None, genre:list=None, url:str=None):
        self.media_id = media_id
        self.media_type = media_type
        self.titles = title
        self.genre = genre
        self.url = url

    def get_name(self):
        for title in self.titles:
            if title is not None:
                return title

class AnimePaginator:
    paginator:SelectPaginator = None
    media:list = None
    media_type:str = None

    def __init__(self, paginator, media:list, media_type:str):
        self.paginator = paginator
        self.media = media
        self.media_type = media_type

    def length(self):
        return len(self.media)

    async def get_error_embed(self):
        return await general_helper.get_information_embed(
            title="Damn",
            description="No {} were found for that input".format(self.media_type),
            color=config.ERROR_COLOR
        )

"""Returns an embed with specified details"""

async def get_information_embed(title:str, color=config.NORMAL_COLOR, url:str=None, description:str=None, user:Member=None, thumbnail_link:str=None, fields:list=None) -> Embed:

    embd:Embed = Embed(title=title, color=color)
    embd.timestamp = datetime.now()

    if url is not None:
        embd.url = url

    if description is not None:
        embd.description = description

    if user is not None:
        embd.set_footer(icon_url=user.avatar.url, text="Requested by {}".format(user.name))

    if thumbnail_link is not None:
        embd.set_thumbnail(url=thumbnail_link)

    if fields is not None:
        for field in fields:
            if len(field) != 3:
                continue

            embd.add_field(
                name=field[0],
                value=field[1],
                inline=field[2]
            )

    return embd

"""Returns the aniList id from anilist username"""

async def get_id_from_anilist_username(username:str) -> int:

    query = """
        query($username:String){
            User(search:$username){
                id
            }
        }
    """

    variables = {
        "username" : username
    }

    resp = requests.post(config.ANILIST_BASE, json={"query" : query, "variables" : variables})

    try:
        return resp.json()["data"]["User"]["id"]
    except Exception as e:
        print(e)
        return None

"""Returns the aniList Id from token"""

async def get_id_from_token(token:str) -> str:
    data = jwt.decode(token, options={"verify_signature": False})

    return data["sub"]

"""Returns the aniList id from userID"""

async def get_id_from_userID(userID:str) -> str:
    
    data = await mongo_manager.manager.get_user(userID)

    if data is not None:
        return data["anilistID"]
    else:
        return None

"""Returns a formatted time string"""

async def get_time_str_from_seconds(seconds:int):

    time_str = ""

    hours = seconds // 3600
    seconds = seconds - hours * 3600
    minutes = seconds // 60
    seconds = seconds - minutes * 60

    time_vals = (hours, minutes, seconds)
    time_markers = ("hours", "minutes", "seconds")

    for i in range(len(time_vals)):
        if time_vals[i] > 0:
            time_str += "{} {} ".format(time_vals[i], time_markers[i])

    return (time_str if time_str != "" else "0 seconds")

"""Check whether the user is registered with AniList account or not"""

async def validate_user(ctx:commands.Context):

    command_user = ctx.author

    data = await mongo_manager.manager.get_user(str(command_user.id))

    if data is None:
        return False

    return True

def short_cooldown():

    return commands.cooldown(rate=1, per=5, type=commands.BucketType.user)

"""Returns a list of anime to select from"""

async def get_media_selection_paginator(media_name:str, select_callback:callable, media_type="ANIME") -> AnimePaginator:

    anime_query = """
        query($search:String, $type:MediaType){
            Page(page:0, perPage:5){
                pageInfo{
                    total
                }
                media(search:$search, sort:SEARCH_MATCH, type:$type){
                    id 
                    title{
                        english
                        romaji
                    }
                    siteUrl
                    genres
                    coverImage{
                        medium
                    }
                    episodes
                    status
                }
            }
        }
    """

    variables = {
        "search" : media_name,
        "type" : media_type
    }

    anime_resp = requests.post(
        url=config.ANILIST_BASE,
        json={
            "query" : anime_query,
            "variables" : variables
        }
    ).json()

    anime_data = anime_resp["data"]["Page"]["media"]

    pages = []
    media_list = []

    for page_data in anime_data:
        embd = Embed(
            title="Which {} are you talking about?".format(media_type),
            color=config.NORMAL_COLOR
        )

        embd.description = "**Name** : [{name}]({url})\n**Episodes** : {episodes}\n**Status** : {status}".format(
            name=(page_data["title"]["english"] if page_data["title"]["english"] is not None else page_data["title"]["romaji"]),
            url=page_data["siteUrl"],
            episodes=page_data["episodes"],
            status=page_data["status"]
        )

        genres = ("\n".join(["{bullet}**{genre}**".format(bullet=config.BULLET_EMOTE, genre=genre) for genre in page_data["genres"]]) if len(page_data["genres"]) > 0 else None)
        embd.add_field(
            name="Genres",
            value=genres,
            inline=False
        )

        embd.set_thumbnail(url=page_data["coverImage"]["medium"])

        pages.append(embd)
        media_list.append(MediaData(page_data["id"]))
        
    if len(pages) > 0:
        paginator = SelectPaginator(pages, select_callback)
    else:
        paginator=None

    return AnimePaginator(paginator, media_list, media_type)
