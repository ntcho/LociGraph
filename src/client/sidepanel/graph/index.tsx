import { useEffect } from "react"
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  useEdgesState,
  useNodesState,
  type EdgeTypes,
  type NodeTypes
} from "reactflow"

import "reactflow/dist/style.css"
import "./index.css"

import type { Relation } from "~types"

import RelationEdge from "./RelationEdge"
import RelationNode from "./RelationNode"

const arrowMarker = {
  type: MarkerType.Arrow,
  width: 24,
  height: 24
}

const nodeTypes: NodeTypes = { relation: RelationNode }
// @ts-ignore
const edgeTypes: EdgeTypes = { relation: RelationEdge }

// helper function to replace spaces with underscores
const get_id = (string: string) => string.replace(/\s+/g, "_")

function RelationGraph({ relations }: { relations: Relation[] }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  useEffect(() => {
    // cooridnates of the next node; add new nodes to the left bottom corner
    let nextX =
      nodes.length === 0 ? 0 : Math.min(...nodes.map((node) => node.position.x))
    let nextY =
      nodes.length === 0 ? 0 : Math.max(...nodes.map((node) => node.position.y))

    const newNodes = []
    const newEdges = []

    for (const relation of relations) {
      const entityId = get_id(relation.entity)
      const valueId = get_id(relation.value)
      const attributeId = get_id(
        `${relation.entity}-${relation.attribute}-${relation.value}`
      )

      // add new nodes if they don't exist
      if (nodes.find((node) => node.id === entityId) === undefined) {
        newNodes.push({
          id: entityId,
          type: "relation",
          position: { x: nextX, y: nextY + 100 },
          data: { label: relation.entity }
        })
      }

      if (nodes.find((node) => node.id === valueId) === undefined) {
        newNodes.push({
          id: valueId,
          type: "relation",
          position: { x: nextX + 200, y: nextY + 100 },
          data: { label: relation.value }
        })
      }

      if (edges.find((edge) => edge.id === attributeId) === undefined) {
        newEdges.push({
          id: attributeId,
          type: "relation",
          source: entityId,
          target: valueId,
          data: { label: relation.attribute },
          markerEnd: arrowMarker
        })
      }

      nextY += 100 // increment y for the next node
    }

    setNodes([...nodes, ...newNodes])
    setEdges([...edges, ...newEdges])
  }, [relations])

  return (
    <ReactFlow
      className="floatingedges"
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      proOptions={{ hideAttribution: true }}
      nodesConnectable={false} // disable editing edges
      fitView>
      <Background />
      <Controls
        className="bg-stone-100 dark:bg-stone-700 rounded-sm"
        position="bottom-right"
      />
    </ReactFlow>
  )
}

export default RelationGraph