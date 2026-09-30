"""Build-time native split patch; fail closed when upstream anchors change."""
from pathlib import Path
import sys
root=Path(sys.argv[1]);assets=Path(__file__).resolve().parents[1]/'frontend'
def edit(relative,fn):
 p=root/relative;s=p.read_text(encoding='utf-8');p.write_text(fn(s),encoding='utf-8',newline='\n')
def replace(s,a,b,count=1):
 if s.count(a)!=count:raise SystemExit('Frontend anchor changed: '+a[:100])
 return s.replace(a,b)
def stores(s):
 s=replace(s,"| 'browser'; // preview", "| 'browser' | 'worker-browser'; // preview")
 # Newer upstream versions also validate persisted tab types.
 if "\n\t'browser'\n" in s:s=s.replace("\n\t'browser'\n","\n\t'browser',\n\t'worker-browser'\n")
 return s+'\n'+(assets/'worker-split.ts').read_text(encoding='utf-8')
edit('src/lib/stores.ts',stores)
def bar(s):
 s=replace(s,'\t\topenBrowserTab,','\t\topenBrowserTab,\n\t\topenWorkerBrowserSplit,')
 s=replace(s,"\t\t\tcase 'browser':", "\t\t\tcase 'worker-browser':\n\t\t\tcase 'browser':")
 anchor='\tconst splitMenuItems = $derived.by(() => {'
 before,after=s.split(anchor)
 after=replace(after,'\t\treturn [','\t\treturn [\n\t\t\t{label: "Arbeiter-Browser rechts", icon: "browser", onclick: () => openWorkerBrowserSplit(group.id,home)},',1)
 s=before+anchor+after
 anchor='\t\t<!-- Split button (wide screens) -->'
 return replace(s,anchor,'\t\t<button class="flex items-center justify-center w-7 h-7 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" aria-label="Arbeiter-Browser rechts öffnen" title="Arbeiter-Browser rechts" onclick={() => openWorkerBrowserSplit(group.id,home)}><Icon name="browser" size={14} /></button>\n'+anchor)
edit('src/lib/components/GroupTabBar.svelte',bar)
def page(s):
 for group in ['homePane','group']:
  anchor="{#each "+group+".tabs.filter((tab) => tab.type === 'browser' && tab.browserSessionId) as tab (tab.id)}"
  block="{#each "+group+".tabs.filter((tab) => tab.type === 'worker-browser') as tab (tab.id)}\n<div class=\"persisted-tab\" class:persisted-tab-hidden={tab.id !== "+group+".activeTabId}><div data-selfwebui-browser-slot={tab.id} style=\"width:100%;height:100%;min-width:0;min-height:0\"></div></div>\n{/each}\n"
  s=replace(s,anchor,block+anchor)
 return s
edit('src/routes/+page.svelte',page)
def approval_default(relative,old,new):
 edit(relative,lambda s:replace(s,old,new))
# New chats start with all tool calls approved; a saved user preference still wins.
approval_default('src/lib/stores.ts',"writable<ToolApprovalMode>('auto')","writable<ToolApprovalMode>('full')")
approval_default('src/lib/components/chat/ChatPanel.svelte',"$state<ToolApprovalMode>('auto')","$state<ToolApprovalMode>('full')")
approval_default('src/lib/components/chat/ChatInput.svelte',"toolApprovalMode = $bindable('auto')","toolApprovalMode = $bindable('full')")
approval_default('src/lib/components/chat/PlusMenu.svelte',"toolApprovalMode = $bindable('auto')","toolApprovalMode = $bindable('full')")

# Sidebar: 20 instead of 5 chats per workspace; the current workspace expands once when it is opened
# (collapsing it again stays possible).
AUTO_EXPAND = """	// Current workspace expands once on first open; collapsing it afterwards stays possible.
	const autoExpandedWorkspaces = new Set<string>();
	$effect(() => {
		const path = currentPath;
		if (!path || autoExpandedWorkspaces.has(path)) return;
		autoExpandedWorkspaces.add(path);
		untrack(() => {
			if (!expandedWorkspaces.has(path)) toggleWorkspaceExpand(path);
		});
	});

"""
def sidebar_chats(s):
 s=replace(s,"import { onDestroy, onMount } from 'svelte';","import { onDestroy, onMount, untrack } from 'svelte';")
 s=replace(s,'const WS_CHATS_PAGE_SIZE = 5;','const WS_CHATS_PAGE_SIZE = 20;')
 # Clicking the name of the workspace that is already open toggles its chat list.
 s=replace(s,"\t\te.preventDefault();\n\t\tgoto(`/?workspace=${encodeURIComponent(path)}`);\n\t\tcloseMobileSidebar();",
  "\t\te.preventDefault();\n\t\tif (path === currentPath) {\n\t\t\ttoggleWorkspaceExpand(path);\n\t\t\treturn;\n\t\t}\n\t\tgoto(`/?workspace=${encodeURIComponent(path)}`);\n\t\tcloseMobileSidebar();")
 anchor='\tasync function fetchWorkspaceChats('
 return replace(s,anchor,AUTO_EXPAND+anchor)
edit('src/lib/components/SidebarWorkspaceList.svelte',sidebar_chats)
print('Native worker-browser tabs and split actions installed')
