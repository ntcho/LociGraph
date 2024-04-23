// From https://reactflow.dev/examples/edges/floating-edges

import { useCallback } from "react"
import { BaseEdge, EdgeLabelRenderer, getBezierPath, useStore } from "reactflow"

import { getEdgeParams } from "./utils.js"

function RelationEdge({ id, source, target, markerEnd, style, data }) {
  const sourceNode = useStore(
    useCallback((store) => store.nodeInternals.get(source), [source])
  )
  const targetNode = useStore(
    useCallback((store) => store.nodeInternals.get(target), [target])
  )

  if (!sourceNode || !targetNode) {
    return null
  }

  const { sx, sy, tx, ty, sourcePos, targetPos } = getEdgeParams(
    sourceNode,
    targetNode
  )

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX: sx,
    sourceY: sy,
    sourcePosition: sourcePos,
    targetPosition: targetPos,
    targetX: tx,
    targetY: ty
  })

  return (
    <>
      <BaseEdge
        id={id}
        // className="react-flow__edge-path"
        path={edgePath}
        markerEnd={markerEnd}
        style={style}
      />
      <EdgeLabelRenderer>
        <div
          className="nodrag nopan px-2 py-1 shadow-md rounded-md border \
          border-stone-400 bg-stone-100 dark:border-stone-500 dark:bg-stone-800 \
          text-xs text-stone-900 dark:text-stone-50"
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`
          }}>
          {data.label}
        </div>
      </EdgeLabelRenderer>
    </>
  )
}

export default RelationEdge
