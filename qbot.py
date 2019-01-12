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
import socket
import re
from discord.ext import commands
import dns.resolver

dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['1.1.1.1'] #cloudflare dns

bot = commands.Bot(command_prefix='!', description='''A simple bot to query Quake 3 servers (protocol 68)''')

aliases = {
    #'alias': '1.1.1.1:27960',
}
nameRegex = '\^+[a-z0-9]'

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    await set_default_status()

@bot.event
async def on_member_join(member):
    name = member.name
    output = 'Welcome ' + name + '!'
    await bot.say(output)

@bot.command()
async def alias():
    aliasesOutput = 'Aliases:'
    for key, value in aliases.items():
        aliasesOutput = aliasesOutput + '\n' + key
    await bot.say(aliasesOutput)

@bot.command()
async def q3(argument: str):

    if argument == 'help':
        await bot.say('Usage: !q3 <alias> or !q3 ip(:port) or !q3 hostname(:port), type !alias to see a list of known aliases')
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

    # get ip and port
    query = queryServer.strip().split(":")
    ip = query[0]
    port = 27960
    if len(query) > 1:
        port = int(query[1])
    if not isValidIp(ip):
        resolvedIps = await resolveHost(ip)
        if len(resolvedIps) == 0:
            await bot.say("I couldn't resolve that domain")
            return
        else:
            ip = resolvedIps[0]

    status = await getServerStatus(ip, port)
    if status is None:
        await bot.say('There was an error fetching server status')
    else:
        serverInfo = status[0]
        playersList = status[1]

        name = re.sub(nameRegex, '', serverInfo['sv_hostname'])
        currentMap = serverInfo['mapname']
        playersNumber = str(len(playersList)) + '/' + serverInfo['sv_maxclients']

        embed = discord.Embed(title=name, description=ip+':'+str(port), colour=0x3c9824, type='rich')
        embed.add_field(name='Map', value=currentMap, inline=True)

        if len(playersList) > 0:
            embed.add_field(name='Players', value=playersNumber, inline=False)
            players = []
            scores = []
            pings = []

            for p in playersList:
                p_name = re.sub(nameRegex, '', p[2])
                players.append(p_name.strip("\""))
                scores.append(p[0])
                pings.append(p[1]+ 'ms')

            embed.add_field(name='Player', value='```http\n' + '\n'.join(players) + '```' , inline=True)
            embed.add_field(name='Score', value='```http\n'  + '\n'.join(scores) + '```' , inline=True)
            embed.add_field(name='Ping', value='```http\n' + '\n'.join(pings) + '```', inline=True)

        await bot.say(embed=embed)

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
    result = dns.resolver.query(domain, "A")
    answer = ''
    ips = []
    for item in result:
        ips.append(str(item))
    return ips

@bot.event
async def set_default_status():
    await bot.change_presence(game=discord.Game(name='noobs getting owned', type=3))

bot.run('<your_token>')