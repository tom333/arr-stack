<script lang="ts">
  import type { JsonSchemaNode, RootSchema } from '../types';
  import { effectiveNode } from '../schema';
  import HelpTooltip from './HelpTooltip.svelte';
  import SuggestArrBadge from './SuggestArrBadge.svelte';
  import FieldInput from './FieldInput.svelte';

  /**
   * D-13 schema-driven widget dispatcher.
   *
   * Walks a JSON Schema node and renders the right HTML widget.
   * NEVER hand-codes a per-field UI — every form input in the application
   * flows through this component.
   *
   * Dispatch rules (per CONTEXT D-13 + UI-SPEC §3):
   *   enum               → <select>
   *   integer            → <input type="number">  (min/max from schema)
   *   boolean            → <input type="checkbox">
   *   string + format    → <input type="text"> (pattern attr)
   *   string             → <input type="text">
   *   array primitives   → comma-separated text
   *   array of objects   → handled by parent (CategoriesEditor / AppSection sub-tables)
   *   object             → recursive nested form
   *   $ref / anyOf       → resolved via effectiveNode() helper
   */
  type Props = {
    schema: JsonSchemaNode;
    root: RootSchema;
    value: unknown;
    onChange: (next: unknown) => void;
    /** Dotted path like "seerr.main.sonarr_service.activeAnimeProfileId" — used by SuggestArrBadge. */
    path: string;
    /** Field label (e.g., "Active Anime Profile Id"). Defaults to the leaf segment of path. */
    label?: string;
    /** Pydantic 422 error message for this exact path, if any. */
    errorMsg?: string;
    /** Show label + help inline? Set false when the parent already rendered the label. */
    showLabel?: boolean;
  };

  let { schema, root, value, onChange, path, label, errorMsg, showLabel = true }: Props = $props();

  const effective = $derived(effectiveNode(schema, root));
  const leafLabel = $derived(label ?? path.split('.').pop()?.replace(/_/g, ' ') ?? path);
  const description = $derived(effective.description ?? '');
  const hasError = $derived(!!errorMsg);

  function handleStringInput(e: Event) {
    onChange((e.target as HTMLInputElement).value);
  }
  function handleNumberInput(e: Event) {
    const raw = (e.target as HTMLInputElement).value;
    onChange(raw === '' ? null : Number(raw));
  }
  function handleBoolInput(e: Event) {
    onChange((e.target as HTMLInputElement).checked);
  }
  function handleSelect(e: Event) {
    onChange((e.target as HTMLSelectElement).value);
  }
  function handleArrayInput(e: Event) {
    // Comma-separated text input for list[int] / list[str].
    const raw = (e.target as HTMLInputElement).value;
    const items = raw
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    // Try to coerce to numbers if the array items hint at numbers.
    const itemsSchema = Array.isArray(effective.items) ? effective.items[0] : effective.items;
    if (itemsSchema?.type === 'integer') {
      onChange(items.map((s) => Number(s)).filter((n) => !Number.isNaN(n)));
    } else {
      onChange(items);
    }
  }
</script>

{#if showLabel && effective.type !== 'object'}
  <label class="field-label" for={path}>
    {leafLabel}
    {#if description}
      <HelpTooltip text={description} />
    {/if}
    <SuggestArrBadge {path} />
  </label>
{/if}

{#if effective.enum}
  <select id={path} class:has-error={hasError} value={value as string} onchange={handleSelect}>
    {#each effective.enum as opt}
      <option value={opt}>{opt}</option>
    {/each}
  </select>
{:else if effective.type === 'integer'}
  <input
    id={path}
    type="number"
    step="1"
    min={effective.minimum}
    max={effective.maximum}
    class:has-error={hasError}
    value={value === null || value === undefined ? '' : (value as number)}
    oninput={handleNumberInput}
  />
{:else if effective.type === 'boolean'}
  <input
    id={path}
    type="checkbox"
    class:has-error={hasError}
    checked={!!value}
    onchange={handleBoolInput}
  />
{:else if effective.type === 'array'}
  <input
    id={path}
    type="text"
    class:has-error={hasError}
    placeholder="comma-separated (e.g., 2, 3)"
    value={Array.isArray(value) ? (value as unknown[]).join(', ') : ''}
    oninput={handleArrayInput}
  />
{:else if effective.type === 'string'}
  <input
    id={path}
    type="text"
    pattern={effective.pattern}
    class:has-error={hasError}
    value={(value ?? '') as string}
    oninput={handleStringInput}
  />
{:else if effective.type === 'object' && effective.properties}
  <fieldset class="nested-object">
    {#if showLabel}
      <legend>
        {leafLabel}
        {#if description}<HelpTooltip text={description} />{/if}
      </legend>
    {/if}
    {#each Object.entries(effective.properties) as [childKey, childSchema]}
      {@const childPath = `${path}.${childKey}`}
      {@const childValue = (value as Record<string, unknown> | null | undefined)?.[childKey]}
      <div class="field-row">
        <FieldInput
          schema={childSchema}
          {root}
          value={childValue}
          onChange={(next: unknown) => {
            const current = (value ?? {}) as Record<string, unknown>;
            onChange({ ...current, [childKey]: next });
          }}
          path={childPath}
        />
      </div>
    {/each}
  </fieldset>
{:else}
  <span class="unsupported">[Unsupported schema node: type={effective.type ?? '?'}]</span>
{/if}

{#if errorMsg}
  <div class="error-msg">Error: {errorMsg}</div>
{/if}

<style>
  .field-label {
    display: inline-flex;
    align-items: center;
    gap: var(--space-xs);
    font-size: 14px;
    margin-right: var(--space-sm);
  }
  .nested-object {
    border: 1px solid var(--color-border);
    border-radius: 4px;
    padding: var(--space-md);
    margin: var(--space-sm) 0;
    background: var(--color-panel);
  }
  .nested-object legend {
    padding: 0 var(--space-sm);
    font-weight: 600;
    font-size: 14px;
  }
  .field-row {
    display: flex;
    flex-direction: column;
    margin-bottom: var(--space-sm);
  }
  .error-msg {
    color: var(--color-destructive);
    font-size: 12px;
    margin-top: var(--space-xs);
  }
  .unsupported {
    color: var(--color-muted);
    font-style: italic;
    font-size: 12px;
  }
</style>
