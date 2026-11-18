"""Cover more immediate opponent replies while keeping internal width seven."""
from agents.ab2_endgame import EndgameAB2
from agents import register
from agents.ab_variants import Variant

@register("ab2replies")
class ReplyCoverageAB2(EndgameAB2):
    def __init__(self,reply_width=32,**kwargs):
        super().__init__(**kwargs)
        if type(reply_width) is not int or not self.width<=reply_width<=64:
            raise ValueError("reply_width must be between internal width and 64")
        self.reply_width=reply_width
        self.reply_table={}
        self.base_table=self.table
        self.root_ply=None

    def new_game(self,position,species,seed):
        super().new_game(position,species,seed)
        self.reply_table.clear();self.base_table=self.table

    def choose_moves(self,node,context):
        active=bool(self.goal_slots and self.mixed_capability(node))
        if active!=self.coverage_active:self.reply_table.clear()
        self.root_ply=node.ply;self.base_table=self.table
        moves=super().choose_moves(node,context)
        self.info.update(reply_width=self.reply_width,internal_width=self.width)
        return moves

    def _plans(self,node):
        if self.reply_width>self.width and node.ply==self.root_ply+1:
            normal=self.width
            try:
                self.width=self.reply_width
                # Use all 32 base candidates here, not a goal-diversified subset
                # that could discard a recorded low-ranked opponent reply.
                return Variant._plans(self,node)
            finally:self.width=normal
        return super()._plans(node)

    def search(self,node,depth,alpha,beta,qleft=0):
        if self.reply_width==self.width:
            return super().search(node,depth,alpha,beta,qleft)
        outer=self.table
        self.table=self.reply_table if node.ply==self.root_ply+1 else self.base_table
        try:return super().search(node,depth,alpha,beta,qleft)
        finally:self.table=outer
