// Native editor group: the existing direct browser is projected into its slot.
export function openWorkerBrowserSplit(targetGroupId?: string, home = false): void {
 const update = (state: WorkspaceState | HomeState) => {
  const existing = state.groups.find(g => g.tabs.some(t => t.type === 'worker-browser'));
  if (existing) return {...state, activeGroupId:existing.id, groups:state.groups.map(g => g.id === existing.id ? {...g,activeTabId:g.tabs.find(t => t.type === 'worker-browser')!.id} : g)};
  const tab: Tab = {id:nextId(),type:'worker-browser',label:'Arbeiter-Browser'};
  const group: EditorGroup = {id:nextId(),tabs:[tab],activeTabId:tab.id};
  return {...state,groups:[...state.groups,group],activeGroupId:group.id,layout:splitLayout(state.layout,targetGroupId ?? state.activeGroupId,group.id,'horizontal'),splitDirection:'horizontal' as SplitDirection};
 };
 if (home) homeState.update(state => update(state) as HomeState);
 else currentWorkspace.update(state => state ? update(state) as WorkspaceState : state);
}

if (typeof window !== 'undefined') {
 window.addEventListener('selfwebui:open-browser', () => openWorkerBrowserSplit(undefined,!get(currentWorkspace)));
 window.addEventListener('selfwebui:close-browser', () => {
  const ws=get(currentWorkspace);
  const state=ws ?? get(homeState);
  for (const group of state.groups) {
   const tab=group.tabs.find(t => t.type === 'worker-browser');
   if (!tab) continue;
   if (group.tabs.length===1) {if(ws) closeGroup(group.id);else closeHomeGroup(group.id);}
   else if(ws) closeTab(tab.id,group.id);
   else homeState.update(s=>({...s,groups:s.groups.map(g=>g.id===group.id?{...g,tabs:g.tabs.filter(t=>t.id!==tab.id),activeTabId:g.tabs.find(t=>t.id!==tab.id)!.id}:g)}));
  }
 });
}
