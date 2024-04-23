import { Handle, Position } from "reactflow"

function RelationNode({ data, type }) {
  return (
    <div
      className="px-4 py-2 shadow-md rounded-md border-2 \
    border-stone-400 bg-stone-50 dark:bg-stone-700">
      <div className="text-sm font-bold text-stone-900 dark:text-stone-50">
        {data.label}
      </div>

      <Handle
        type="source"
        position={Position.Right} // invisible via index.css
      />

      <Handle
        type="target"
        position={Position.Left} // invisible via index.css
      />
    </div>
  )
}

export default RelationNode
