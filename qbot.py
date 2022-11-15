# Copyright (c) 2022 Andrea Giavatto

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
import socket
import re
from discord.ext import commands
import dns.resolver
import numpy as np

dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['1.1.1.1'] #cloudflare dns

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, description='''A simple bot to query Quake 3 servers (protocol 68)''')

aliases = {
    #'alias': '1.1.1.1:27960'
}
nameRegex = '\^+[a-z0-9]'

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

@bot.command()
async def alias(context):
    embed = discord.Embed(title='', description='', colour=0x3c9824, type='rich')
    sorted_keys = sorted(list(aliases.keys()), key=str.lower)
    names = []
    ips = []
    for key in sorted_keys:
        names.append(key)
        ips.append(aliases[key])
    embed.add_field(name='Alias', value='\n'.join(names), inline=True)
    embed.add_field(name='Hostname', value='\n'.join(ips), inline=True)
    await context.send(embed=embed)

@bot.command()
async def q3(context, argument: str):
    if argument == 'help':
        await context.send('Usage: !q3 <alias> or !q3 ip(:port) or !q3 hostname(:port), type !alias to see a list of known aliases')
        return
    
    queryServer = argument
    for key, value in aliases.items(): # check if alias first
        if key == argument:
            queryServer = value
            break

    # get ip and port
    query = queryServer.strip().split(":")
    ip = query[0]
    port = 27960
    if len(query) > 1:
        port = int(query[1])
    if not isValidIp(ip):
        resolvedIps = await resolveHost(ip)
        if len(resolvedIps) == 0:
            await context.send("I couldn't resolve that domain")
            return
        else:
            ip = resolvedIps[0]

    status = await getServerStatus(ip, port)

    if status is None:
        await context.send('There was an error fetching server status')
    else:
        serverInfo = status[0]
        playersList = status[1]

        name = re.sub(nameRegex, '', serverInfo['sv_hostname'])
        currentMap = serverInfo['mapname']
        
        embed = discord.Embed(title=name, description=ip+':'+str(port), colour=0x3c9824, type='rich')
        embed.add_field(name='Map', value=currentMap, inline=True)

        is_team_game = serverInfo['g_gametype'] == '3' or serverInfo['g_gametype'] == '4'
        if is_team_game:
            customiseEmbedForTeamGame(embed, serverInfo, playersList)
        else:
            customiseEmbedForGenericGame(embed, serverInfo, playersList)

        await context.send(embed=embed)

def customiseEmbedForTeamGame(embed, serverInfo, playersList):
    if len(playersList) > 0:
        playersNumber = str(len(playersList)) + '/' + serverInfo['sv_maxclients']
        embed.add_field(name='Players', value=playersNumber, inline=True)

        score_red = serverInfo['score_red']
        score_blue = serverInfo['score_blue']
        embed.add_field(name='Score Red', value=score_red, inline=False)
        embed.add_field(name='Score Blue', value=score_blue, inline=False)

        if 'players_blue' in serverInfo and 'players_red' in serverInfo:
            players_in_blue_team = serverInfo['players_blue'].split()
            players_in_red_team = serverInfo['players_red'].split()
            team_red = []
            team_blue = []
            team_spec = []
            for index, player in enumerate(playersList):
                if str(index + 1) in players_in_blue_team:
                    team_blue.append(player)
                elif str(index + 1) in players_in_red_team:
                    team_red.append(player)
                else:
                    team_spec.append(player)
        
            sortPlayersByScore(team_red)
            addPlayersToEmbed(embed, team_red, 'Team Red')
            addPlayersToEmbed(embed, team_blue, 'Team Blue')
            if len(team_spec) > 0:
                addPlayersToEmbed(embed, team_spec, 'Spectators')
        else: # all players in spec
            addPlayersToEmbed(embed, playersList, 'Spectators')

def customiseEmbedForGenericGame(embed, serverInfo, playersList):
    if len(playersList) > 0:
        playersNumber = str(len(playersList)) + '/' + serverInfo['sv_maxclients']
        embed.add_field(name='Players', value=playersNumber, inline=False)
        addPlayersToEmbed(embed, playersList, 'Player')

def addPlayersToEmbed(embed, playersList, teamName):
    sorted = sortPlayersByScore(playersList)

    embed.add_field(name=teamName, value='```\n' + '\n'.join(sorted[0]) + '```' , inline=True)
    embed.add_field(name='Score', value='```\n'  + '\n'.join(sorted[1]) + '```' , inline=True)
    embed.add_field(name='Ping', value='```\n' + '\n'.join(sorted[2]) + '```', inline=True)

def sortPlayersByScore(playersList):
    sorted_players = []
    sorted_scores = []
    sorted_pings = []
    players = []
    scores = []
    pings = []
    if len(playersList) > 0:
        for p in playersList:
            p_name = re.sub(nameRegex, '', p[2])
            players.append(p_name.strip("\""))
            scores.append(int(p[0]))
            pings.append(p[1]+ 'ms')
    converted_scores = np.array(scores)
    indexes = np.argsort(converted_scores)
    reversed_indexes = indexes[::-1]
    for i in reversed_indexes:
        sorted_players.append(players[i])
        sorted_scores.append(str(scores[i]))
        sorted_pings.append(pings[i])
    return (sorted_players, sorted_scores, sorted_pings)

async def getServerStatus(ip: str, port: int):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect((ip, port))
        getStatus = bytes([0xff, 0xff, 0xff, 0xff, 0x67, 0x65, 0x74, 0x73, 0x74, 0x61, 0x74, 0x75, 0x73, 0x0a])
        sock.send(getStatus)
        response = sock.recvfrom(2048) # response is (string, address) where address is (host, port) for AF_INET family
        underline_bytes = response[0]
        return parseResponse(underline_bytes.decode("latin_1"))

    except socket.error as e:
        print(e)
        return None

def parseResponse(response: str):
    lines = response.split('\n')
    lines = lines[1:] # first element is 'ÿÿÿÿstatusResponse', followed by server cfg then optionally players
    serverVars = parseServerInfo(lines[0])
    players = []
    if len(lines) > 1: # there are players/bots
        players = parsePlayers(lines[1:])
    return (serverVars, players)

def parseServerInfo(serverData: str):
    data = serverData.split('\\')
    data = data[1:] # first element is empty as string starts with \\
    serverInfo = {}
    # if len(data) % 2 == 0: # must be even number now
    for i in range(0, len(data), 2):
        key = data[i]
        value = data[i+1]
        serverInfo[key] = value

    return serverInfo

def parsePlayers(playersList: [str]):
    players = []
    for p in playersList:
        if len(p) > 0:
            playerData = p.split() # score ping name
            players.append(playerData)
    return players

def isValidIp(ip: str):
   components = ip.strip().split(".")
   return len(components) == 4

async def resolveHost(domain: str):
    result = dns.resolver.resolve(domain, "A")
    answer = ''
    ips = []
    for item in result:
        ips.append(str(item))
    return ips

@bot.event
async def set_default_status():
    await bot.change_presence(game=discord.Game(name='noobs getting owned', type=3))

bot.run('your_token_here')