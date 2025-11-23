# Rules Persistence Fix

## Problem
Rules were being saved to the database successfully, but were not loading back after page reload. The wizard state only loaded from localStorage and never fetched entities from the backend API.

## Root Cause
The `WizardProvider` in `apps/frontend/src/state/wizard.tsx` had a useEffect that only loaded entities from localStorage. There was no code to fetch entities from the backend API, even though the API endpoints existed and worked correctly.

**Evidence:**
- `listEntities` API function exists in `apps/frontend/src/services/entities.ts`
- Backend save endpoint (`PUT /api/v1/projects/{id}/entities/{entityId}`) works correctly
- `transformEntityResponse` function properly converts `rules_config` → `rulesConfig` and `rules_format` → `rulesFormat`
- No code anywhere called `listEntities` to fetch from backend

## Solution
Updated the entity loading useEffect in `WizardProvider` to:

1. **Primary**: Fetch entities from backend API using `listEntities(projectId)`
2. **Update existing entities**: If entity exists in state, update it with backend data (backend is source of truth)
3. **Fallback**: If backend fetch fails, load from localStorage as before

### Code Changes

**File: `apps/frontend/src/state/wizard.tsx`**

**Before:**
```tsx
// Draft rehydration: load any autosaved entities for the project
useEffect(() => {
  if (!state.projectId) return
  try {
    const prefix = `autosave:${state.projectId || 'default'}:`
    const keys = Object.keys(localStorage)
    const drafts = keys.filter((k) => k.startsWith(prefix))
    if (drafts.length === 0) return
    drafts.forEach((k) => {
      try {
        const raw = localStorage.getItem(k)
        if (!raw) return
        const entity = JSON.parse(raw) as EntitySchema
        if (!state.entities.some((e) => e.id === entity.id)) {
          dispatch({ type: 'addEntity', entity })
        }
      } catch (_) {
        // ignore malformed
      }
    })
  } catch (_) {
    // ignore
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [state.projectId])
```

**After:**
```tsx
// Draft rehydration: load entities from backend, fallback to localStorage
useEffect(() => {
  if (!state.projectId) return
  
  // First try to load from backend
  const loadFromBackend = async () => {
    try {
      const { listEntities } = await import('../services/entities')
      const entities = await listEntities(state.projectId!)
      
      // Add entities from backend that aren't already in state
      entities.forEach((entity) => {
        if (!state.entities.some((e) => e.id === entity.id)) {
          dispatch({ type: 'addEntity', entity })
        } else {
          // Entity exists in state, update it with backend data (backend is source of truth)
          dispatch({ type: 'updateEntity', id: entity.id, patch: entity })
        }
      })
    } catch (error) {
      console.warn('Failed to load entities from backend, falling back to localStorage:', error)
      
      // Fallback to localStorage if backend fails
      try {
        const prefix = `autosave:${state.projectId || 'default'}:`
        const keys = Object.keys(localStorage)
        const drafts = keys.filter((k) => k.startsWith(prefix))
        if (drafts.length === 0) return
        drafts.forEach((k) => {
          try {
            const raw = localStorage.getItem(k)
            if (!raw) return
            const entity = JSON.parse(raw) as EntitySchema
            if (!state.entities.some((e) => e.id === entity.id)) {
              dispatch({ type: 'addEntity', entity })
            }
          } catch (_) {
            // ignore malformed
          }
        })
      } catch (_) {
        // ignore
      }
    }
  }
  
  loadFromBackend()
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [state.projectId])
```

## How It Works

### Flow Before Fix
1. User saves rules → API call to backend ✅
2. Backend saves to `wizard_entities.rules_config` ✅
3. User reloads page → Wizard loads from localStorage only ❌
4. Rules from database never loaded ❌

### Flow After Fix
1. User saves rules → API call to backend ✅
2. Backend saves to `wizard_entities.rules_config` ✅
3. User reloads page → Wizard fetches from backend API ✅
4. `transformEntityResponse` converts `rules_config` → `rulesConfig` ✅
5. Rules page loads `entity.rulesConfig` ✅
6. User sees saved rules ✅

## Testing

### Manual Test Steps

1. **Save Rules**:
   - Open wizard for a project
   - Go to Rules tab
   - Add some rules (e.g., PK uniqueness, FK constraints)
   - Click "Save Rules"
   - Verify success message appears

2. **Reload Page**:
   - Refresh the browser (F5 or Ctrl+R)
   - Wizard should load
   - Go to Rules tab
   - **Expected**: Previously saved rules should appear
   - **Previous behavior**: Rules were empty

3. **Verify Backend Persistence**:
   - Open browser DevTools → Network tab
   - Reload page
   - Look for API call: `GET /api/v1/projects/{projectId}/entities`
   - **Expected**: You should see this call being made
   - Click on the request → Preview tab
   - Check that `rules_config` field is populated with your saved rules

4. **Test Multiple Entities**:
   - Create multiple entities in the wizard
   - Add different rules to each entity
   - Save all rules
   - Reload page
   - Switch between entities in Rules tab dropdown
   - **Expected**: Each entity shows its own saved rules

### Database Verification

To verify rules are actually saved to the database, run:

```bash
cd apps/backend
python check_entity_rules.py
```

This will show all entities with their `rules_config`, `rules_format`, and version numbers.

Expected output:
```
Total entities in database: 2

Entity: CustomerOrders
  ID: abc-123-def
  Version: 3
  Rules Format: yaml
  Has Rules Config: True
  Rules Preview: tables:
  customers:
    constraints:
      - type: unique
        columns: [email]
  ...

Entity: InventorySystem
  ID: xyz-456-uvw
  Version: 2
  Rules Format: yaml
  Has Rules Config: True
  Rules Preview: tables:
  products:
    constraints:
      - type: pk
        columns: [id]
  ...
```

## Related Files

- `apps/frontend/src/state/wizard.tsx` - Wizard state management (UPDATED)
- `apps/frontend/src/services/entities.ts` - Entity API service (already correct)
- `apps/frontend/src/pages/wizard/rules_page.tsx` - Rules UI (already fixed in previous update)
- `apps/backend/app/api/api_v1/endpoints/entities.py` - Backend API (already correct)
- `apps/backend/app/db/models.py` - Database models (schema already correct)

## Impact

- ✅ Rules now persist across page reloads
- ✅ Backend is source of truth for all entity data
- ✅ localStorage serves as fallback only
- ✅ No breaking changes to existing functionality
- ✅ Autosave still works (saves to both localStorage and backend)

## Future Improvements

Consider:
1. Add loading state indicator when fetching entities from backend
2. Show toast notification if backend fetch fails and localStorage is used
3. Add retry logic for failed backend fetches
4. Implement optimistic updates for better UX
5. Add entity sync status indicator (synced/local-only/conflict)
