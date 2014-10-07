from framework.dependency_management.dependency_resolver import ServiceLocator

"""
owtf is an OWASP+PTES-focused try to unite great tools and facilitate pen testing
Copyright (c) 2011, Abraham Aranguren <name.surname@gmail.com> Twitter: @7a_ http://7-a.org
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the copyright owner nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

ACTIVE Plugin for Testing for HTTP Methods and XST (OWASP-CM-008)
"""

from framework.lib.general import get_random_str


DESCRIPTION = "Active probing for HTTP methods"


def run(PluginInfo):
    # Transaction = Core.Requester.TRACE(Core.Config.Get('host_name'), '/')
    target = ServiceLocator.get_component("target")
    URL = target.Get('top_url')
    # TODO: PUT not working right yet
    # PUT_URL = URL+"/_"+get_random_str(20)+".txt"
    # print PUT_URL
    # PUT_URL = URL+"/a.txt"
    # PUT_URL = URL
    plugin_helper = ServiceLocator.get_component("plugin_helper")
    Content = plugin_helper.TransactionTableForURL(
        True,
        URL,
        Method='TRACE')
    # Content += Core.PluginHelper.TransactionTableForURL(
    #    True,
    #    PUT_URL,
    #    Method='PUT',
    #    Data=get_random_str(15))
    resource = ServiceLocator.get_component("resource")
    Content += plugin_helper.CommandDump(
        'Test Command',
        'Output',
        resource.GetResources('ActiveHTTPMethods'),
        PluginInfo,
        Content)
    return Content
