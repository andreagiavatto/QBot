# Copyright (c) 2018 Andrea Giavatto

# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import discord
import asyncio
import json
import urllib.request
import re
from discord.ext import commands

bot = commands.Bot(command_prefix='!', description='''A simple bot to query Quake 3 servers using gameapis.net''')

aliases = {
    # alias as 'alias': '1.1.1.1:1111'
}
nameRegex = '\^+[a-z0-9]'

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

@bot.command()
async def qinfo(argument: str):
    if argument == 'help':
        await bot.say('Usage: !qinfo <alias> or !qinfo ip:port, type !qinfo aliases to print a list of known aliases')
        return

    if argument == 'aliases':
        aliasesOutput = 'Aliases:'
        for key, value in aliases.items():
            aliasesOutput = aliasesOutput + '\n' + key
        await bot.say(aliasesOutput)
        return

    if argument == '127.0.0.1':
        await bot.say('There is no place like home')
        return

    # check if alias first
    queryServer = argument
    for key, value in aliases.items():
        if key == argument:
            queryServer = value
            break

    queryUrl = 'https://use.gameapis.net/quake3/query/info/' + queryServer
    with urllib.request.urlopen(queryUrl) as url:
        s = url.read()
        response = json.loads(s)
        if response:
            name = re.sub(nameRegex, '', response['name'])
            host = response['hostname']
            port = str(response['port'])
            currentMap = response['map']
            playersNumber = str(response['players']['online']) + '/' + response['players']['max']

            embed = discord.Embed(title=name, description='', colour=0x3c9824)
            embed.add_field(name='Server IP', value=host+':'+port, inline=True)
            embed.add_field(name='Map', value=currentMap, inline=True)
            embed.add_field(name='Players', value=playersNumber, inline=True)

            playersList = response['players']['list']
            players = []
            scores = []
            pings = []

            for p in playersList:
                players.append(re.sub(nameRegex, '', p['name']))
                scores.append(p['frags'])
                pings.append(p['ping']+ 'ms')
            
            embed.add_field(name='Player', value='\n'.join(players), inline=True)
            embed.add_field(name='Score', value='\n'.join(scores), inline=True)
            embed.add_field(name='Ping', value='\n'.join(pings), inline=True)

            await bot.say(embed=embed)
        else:
            await bot.say('Invalid ip or alias')

bot.run('your_token')