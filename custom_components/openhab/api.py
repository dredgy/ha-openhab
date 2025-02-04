"""Sample API Client."""
from __future__ import annotations

import base64
from typing import Any

import os
import aiohttp
import pathlib
import json

from .utils import strip_ip
import aiohttp
import base64
import logging

from openhab import (
    OpenHAB,
    oauth2_helper
)

from .const import CONF_AUTH_TYPE_BASIC, CONF_AUTH_TYPE_TOKEN
from homeassistant.helpers.storage import STORAGE_DIR, _LOGGER

API_HEADERS = {aiohttp.hdrs.CONTENT_TYPE: "application/json; charset=UTF-8"}

def get_model_name(a, b):
    sim = 0
    for r in range(min(len(a), len(b))):
        if a[r] == b[r]:
            sim += 1
        else:
            break

    return (a[:sim]).rstrip('_')

def get_from_Things(oh):
    devi_things = {}

    try:
        things = oh.req_get("/things/")
    except:
        things = False

    if things:
        for thing in things:
            if thing['thingTypeUID']=='danfoss:devismart':
                s1 = ''
                s2 = ''

                #thing['label']
                #thing['properties']
                #thing['statusInfo']
                for ch in thing['channels']:
                    if ch['channelTypeUID'] == 'danfoss:control_mode':
                        s1 = ch['linkedItems'][0]

                    if ch['channelTypeUID'] == 'danfoss:control_state':
                        s2 = ch['linkedItems'][0]

                model = get_model_name(s1, s2)

                devi_things[model]={
                    'label'         : thing['label'],
                    'properties'    : thing['properties'],
                    'statusInfo'    : thing['statusInfo']
                }

    return devi_things

def isDeviDevice(k, devi_things):
    if devi_things:
        return k in devi_things
    else:
        return k.find('DeviReg')==0

def fetch_all_items_new(oh):
    try:
        return fetch_all_items(oh)
    except:
        return {}

def fetch_all_items(oh):
    import json

    dr = {}
    devi_things = get_from_Things(oh)
    items = oh.fetch_all_items()

    for k,v in items.items():
        n = type(v).__name__
        v.type_ex = False
        v.parent_device_name = False

        if n=='GroupItem' and isDeviDevice(k, devi_things):
            x = oh.get_item(k)
            dr[k]=x
            x.type_ex = 'devireg_unit'

    for k,v in items.items():
        is_devi_attr = False
        is_devi_unit = False

        # devireg object
        if k in dr:
            is_devi_unit = True

        if len(v.groupNames)>0:
            if v.groupNames[0] in dr:
                is_devi_attr = True
                v.parent_device_name = v.groupNames[0]

                if v.label in [
                        'State',  'Mode', 'Room temperature', 'Floor temperature',
                        'Heater on time in last 7 days', 'Heater on time in last 30 days', 'Total heater on time']:
                    v.type_ex = 'devireg_attr_ui_sensor'
                elif v.label in ['Heating state', 'Window open']:
                    v.type_ex = 'devireg_attr_ui_binary_sensor'
                elif v.label in ['Enable minimum floor temperature', 'Open window detection', 'Screen lock', 'Temperature forecasting']:
                    v.type_ex = 'devireg_attr_ui_switch'
                else:
                    v.type_ex = 'devireg_attr'


        if is_devi_unit==False:
            dr[k]=v

    copy_attrs = ['minimum', 'maximum','step','readOnly']
    for k,v in dr.items():
        if v.type_ex=='devireg_unit':
            attrs = {}
            full_info = False
            j = oh.req_get(f"/items/{k}")
            if 'members' in j:
                full_info = j['members']

            for m,mv in v._members.items():
                if m.startswith(k):
                    attr = {
                        'name' : m[len(k)+1:],
                        'value': mv._state,
                        'unit' : mv._unitOfMeasure,
                        'type' : mv.type_
                    }

                    if full_info:
                        for x in full_info:
                            if x['name']==m:
                                if 'label' in x:
                                    attr['label']=x['label']

                                if 'stateDescription' in x:
                                    sd = x['stateDescription']

                                    for a in copy_attrs:
                                        if a in sd:
                                            attr[a] = sd[a]

                                    if 'options' in sd:
                                        if len(sd['options'])>0:
                                            attr['options']=sd['options']

                    attrs[attr['name']]=attr

            if k in devi_things:
                thing = devi_things[k]
            else:
                thing = {}

            v.devireg = {
                'attrs': attrs,
                'thing': thing,
                'name_id': k
            }

    return dict(sorted(dr.items()))

async def async_get_item_image(self, item_name: str) -> bytes | None:
    """Fetch image for a specific item."""
    try:
        # Fetch the full item details
        url = f"{self.base_url}/rest/items/{item_name}"
        async with self.session.get(url) as response:
            if response.status == 200:
                item_data = await response.json()
                state = item_data.get('state', '')

                # Check if it's a base64 image
                if state.startswith('data:image'):
                    # Split the data URL and decode the base64 part
                    _, base64_image = state.split(',', 1)
                    return base64.b64decode(base64_image)

            _LOGGER.warning(f"Failed to fetch image for {item_name}: {response.status}")
            return None
    except Exception as err:
        _LOGGER.error(f"Error fetching image for {item_name}: {err}")
        return None

class ApiClientException(Exception):
    """Api Client Exception."""


class OpenHABApiClient:
    """API Client"""

    oauth2_token: str | None

    def CreateOpenHab(self):
        if self.openhab:
            return

        oauth2_config = {
            'client_id': self.oauth2_client_id,
            'token_cache': str(self.oauth2_token_cache)
        }

        timeout = 10

        # try OAuth2 with just name and pswd
        if self._auth_type == CONF_AUTH_TYPE_BASIC and self.auth2 and len(self._username)>0:
            if self._creating_token:
                if os.path.isfile(self.oauth2_token_cache):
                    os.remove(self.oauth2_token_cache)
                return

            # this must be set for oauthlib to work on http (do not set for https!)
            os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

            if not os.path.isfile(self.oauth2_token_cache):
                print('reinstall integration please')
                return
            else:
                with self.oauth2_token_cache.open('r') as fhdl:
                    oauth2_config['token'] = json.load(fhdl)

            self.openhab = OpenHAB(base_url=self._rest_url, oauth2_config=oauth2_config, timeout=timeout)
        else:
            if self._auth_type == CONF_AUTH_TYPE_TOKEN and self._auth_token is not None:
                API_HEADERS["X-OPENHAB-TOKEN"] = self._auth_token
                self.openhab = OpenHAB(self._rest_url, timeout=timeout)

            if self._auth_type == CONF_AUTH_TYPE_BASIC:
                if self._username is not None and len(self._username) > 0:
                    self.openhab = OpenHAB(self._rest_url, self._username, self._password, timeout=timeout)
                else:
                    self.openhab = OpenHAB(self._rest_url, timeout=timeout)


    # pylint: disable=R0913
    def __init__(
        self,
        hass,
        base_url: str,
        auth_type: str,
        auth_token: str | None,
        username: str | None,
        password: str | None,
        creating_token = False
    ) -> None:
        """openHAB API Client."""
        self.hass = hass
        self._base_url = base_url
        self._rest_url = f"{base_url}/rest"
        self._username = username
        self._password = password
        self._auth_type  = auth_type
        self._auth_token = auth_token
        self._creating_token = creating_token

        self.oauth2_token_cache  = pathlib.Path(hass.config.path(STORAGE_DIR, f".{strip_ip(base_url)}_openhub-token-cache"))
        self.oauth2_client_id    = f"{base_url}/auth"

        self.auth2 = True
        self.openhab = False
        self.CreateOpenHab()


    async def async_get_auth2_token(self) -> str:
        self._creating_token = False

        if self.auth2 and len(self._username)>0:
            oauth2_token = await self.hass.async_add_executor_job(oauth2_helper.get_oauth2_token, self._base_url, self._username, self._password)
            if oauth2_token:
                with self.oauth2_token_cache.open('w') as fhdl:
                    json.dump(oauth2_token, fhdl, indent=2, sort_keys=True)

                return True
        return False

    async def async_get_version(self) -> str:
        """Get all items from the API."""
        info = await self.hass.async_add_executor_job(self.openhab.req_get, "/")
        runtime_info = info["runtimeInfo"]
        return f"{runtime_info['version']} {runtime_info['buildString']}"

    async def async_get_item_image(self, item_name: str) -> bytes | None:
        """Fetch image for a specific item."""
        try:
            # Construct the full URL to fetch the item
            url = f"{self._rest_url}/items/{item_name}"

            # Prepare headers
            headers = {}
            if self._auth_token:
                headers['Authorization'] = f'Bearer {self._auth_token}'

            # Use aiohttp to make the request
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        item_data = await response.json()
                        state = item_data.get('state', '')

                        # Check if it's a base64 image
                        if state.startswith('data:image'):
                            # Split the data URL and decode the base64 part
                            _, base64_image = state.split(',', 1)
                            return base64.b64decode(base64_image)

                    _LOGGER.warning(f"Failed to fetch image for {item_name}: {response.status}")
                    return None
        except Exception as err:
            _LOGGER.error(f"Error fetching image for {item_name}: {err}")
            return None

    async def async_get_items(self) -> dict[str, Any]:
        """Get all items from the API."""
        return await self.hass.async_add_executor_job(fetch_all_items_new, self.openhab)

    async def async_get_item(self, item_name: str) -> dict[str, Any]:
        """Get item from the API."""
        return await self.hass.async_add_executor_job(self.openhab.get_item, item_name)

    async def async_send_command(self, item_name: str, command: str) -> None:
        """Set Item state"""
        item = await self.hass.async_add_executor_job(self.async_get_item, item_name)
        await item.command(command)

    async def async_update_item(self, item_name: str, command: str) -> None:
        """Set Item state"""
        item = await self.hass.async_add_executor_job(self.async_get_item, item_name)
        await item.update(command)
