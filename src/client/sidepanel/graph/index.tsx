import { useEffect, useMemo, useState } from "react"
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  Panel,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  useStore,
  type EdgeTypes,
  type NodeTypes
} from "reactflow"

import "reactflow/dist/style.css"
import "./index.css"

import {
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY
} from "d3-force"
import { GroupIcon, LoaderCircle, Moon, Sun } from "lucide-react"

import { Button } from "~components/ui/button"
import type { Relation } from "~types"

import { collide } from "./collide.js"
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

  // @ts-expect-error
  const [initialised, { toggle, isRunning }] = useLayoutedElements()

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

  const [isOrganizing, setOrganizing] = useState(false)

  const organizeGraph = () => {
    if (isOrganizing) return

    setOrganizing(true)
    toggle()

    setTimeout(() => {
      toggle()
      setOrganizing(false)
    }, 2000)
  }

  return (
    <ReactFlow
      className="rounded-md border border-stone-200 dark:border-stone-800 floatingedges"
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      proOptions={{ hideAttribution: true }}
      nodesConnectable={false} // disable editing edges
      fitView>
      <Panel position="top-right">
        {initialised && (
          <Button
            variant="outline"
            size="icon"
            onClick={organizeGraph}
            disabled={isOrganizing}>
            {isOrganizing ? (
              <LoaderCircle className="h-5 w-5 animate-spin" />
            ) : (
              <GroupIcon className="h-5 w-5" />
            )}
          </Button>
        )}
      </Panel>
      <Background />
      <Controls
        className="bg-stone-100 dark:bg-stone-700 rounded-sm"
        position="bottom-right"
      />
    </ReactFlow>
  )
}

function RelationGraphWithProvider({ relations }: { relations: Relation[] }) {
  return (
    <ReactFlowProvider>
      <RelationGraph relations={relations} />
    </ReactFlowProvider>
  )
}

// From https://reactflow.dev/learn/layouting/layouting#d3-force

const simulation = forceSimulation()
  .force("charge", forceManyBody().strength(-1000))
  .force("x", forceX().x(0).strength(0.05))
  .force("y", forceY().y(0).strength(0.05))
  .force("collide", collide())
  .alphaTarget(0.05)
  .stop()

const useLayoutedElements = () => {
  const { getNodes, setNodes, getEdges, fitView } = useReactFlow()
  const initialised = useStore((store) =>
    [...store.nodeInternals.values()].every((node) => node.width && node.height)
  )

  return useMemo(() => {
    let nodes = getNodes().map((node) => ({
      ...node,
      x: node.position.x,
      y: node.position.y
    }))
    let edges = getEdges().map((edge) => edge)
    let running = false

    // If React Flow hasn't initialised our nodes with a width and height yet, or
    // if there are no nodes in the flow, then we can't run the simulation!
    if (!initialised || nodes.length === 0) return [false, {}]

    simulation.nodes(nodes).force(
      "link",
      forceLink(edges)
        // @ts-ignore
        .id((d) => d.id)
        .strength(0.05)
        .distance(50)
    )

    // The tick function is called every animation frame while the simulation is
    // running and progresses the simulation one step forward each time.
    const tick = () => {
      getNodes().forEach((node, i) => {
        const dragging = Boolean(
          document.querySelector(`[data-id="${node.id}"].dragging`)
        )

        // Setting the fx/fy properties of a node tells the simulation to "fix"
        // the node at that position and ignore any forces that would normally
        // cause it to move.

        // @ts-ignore
        nodes[i].fx = dragging ? node.position.x : null
        // @ts-ignore
        nodes[i].fy = dragging ? node.position.y : null
      })

      simulation.tick()
      setNodes(
        nodes.map((node) => ({ ...node, position: { x: node.x, y: node.y } }))
      )

      window.requestAnimationFrame(() => {
        // Give React and React Flow a chance to update and render the new node
        // positions before we fit the viewport to the new layout.
        fitView()

        // If the simulation hasn't be stopped, schedule another tick.
        if (running) tick()
      })
    }

    const toggle = () => {
      running = !running
      running && window.requestAnimationFrame(tick)
    }

    const isRunning = () => running

    return [true, { toggle, isRunning }]
  }, [initialised])
}

export default RelationGraphWithProvider
