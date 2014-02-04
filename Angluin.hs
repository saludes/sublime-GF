{-# LANGUAGE GADTs #-}
module Angluin where
import Data.Map ( empty, fromList, (!), toList, lookup, Map() )
import Prelude hiding ( init, lookup )
import Data.List ( inits, nub, intersperse )
import Data.Maybe ( catMaybes )
import System.Process

type Sq a = [a]

data Learner a = Ord a => L {
	alphabet :: [a],
	start :: [Sq a],
	end :: [Sq a],
	table :: Map (Sq a) Bool
}

type State = Int
type Alphabet a = [a]

data FSA a = F {
	states :: [State],
	begin :: State,
	accepting :: [State],
	transition :: Map (State, a) State
}


type Teacher a = Sq a -> IO Bool
type Oracle a = FSA a -> IO (Maybe (Sq a))

consistent, closed :: Ord a => Learner a -> Bool

mkFSA :: Ord a => Learner a -> FSA a
init :: Ord a => Alphabet a -> Teacher a -> IO (Learner a)
step :: Ord a => Teacher a -> Learner a -> IO (Either (Learner a) (FSA a))

memoized :: Ord a => Learner a -> Teacher a -> Teacher a
memoized l f s = maybe (f s) return $ lookup s (table l)
	

init alpha tea = do
	tt <- mapM f ss
	return $ L alpha none none (fromList tt)
 where
 	f s = tea s >>= (\b -> return (s,b))
	none = [[]]
	ss = []:[[a] | a <- alpha] 

trans :: Ord a => Learner a -> Sq a -> Sq a -> Bool
hash :: [Bool] -> State
row :: Ord a => Learner a -> Sq a -> State

trans l s e = table l ! (s ++ e)
hash = foldl (\a b -> 2*a + if b then 1 else 0) 0 
row l s = hash [trans l s e | e <- end l]


mkFSA l = F q q0 f delta where
	rl = row l
	qs = [(rl s, s) | s <- start l]
	q = nub $ map fst qs
	q0 = rl []
	f = nub $ map fst $ filter (\rs -> trans l (snd rs) []) qs
	delta = fromList [((r,a), rl (s ++ [a])) | a <- alphabet l, (r,s) <- qs]


wit_consistent :: Ord a => Learner a -> [(Sq a, Sq a, a)]
wit_closed :: Ord a => Learner a -> [Sq a]
wit_consistent l = 
 [(s1,s2,a) | a <- alpha, s1 <- st, s2 <- st, s1 /= s2 && rl s1 == rl s2 && tt s1 [a] /= tt s2 [a]]
  where
  	alpha = alphabet l
  	st = start l
  	rl = row l
  	tt = trans l

consistent = null . wit_consistent

wit_closed l = filter f sas
  where
  	alpha = alphabet l
  	st = start l
  	rl = row l
 	sas = [s++[a] | a <- alpha, s <- st]
 	rs = map rl st
 	f sa = let rsa = rl sa in all (/= rsa) rs

closed = null . wit_closed


step tea l | not (consistent l) = do
	l' <- extend tea $ l {end = [a]:et}
	return $ Left l'
  where
  	alpha = alphabet l
	st = start l
	rl = row l
	et = end l
	tt = (table l !)
	(s1,s2,a) = head $ wit_consistent l

step tea l | not (closed l) = do
	l' <- extend tea $ l {start = sa:st}
	return $ Left l'
  where
  	st = start l
  	rl = row l
  	alpha = alphabet l
  	rs = map rl st
  	f rsa = all (/= rsa) rs 
  	sa = head $ wit_closed l

step _ l | otherwise = return $ Right $ mkFSA l

extend :: Ord a => Teacher a -> Learner a -> IO (Learner a)
counterexample :: Eq a => Sq a -> Learner a -> Learner a

membershipLoop :: Ord a => Learner a -> Teacher a -> IO (FSA a, Learner a)
mainLoop :: Ord a => Alphabet a -> (Teacher a, Oracle a) -> IO (Learner a)

membershipLoop l tea = do
	el <- step tea l
	case el of
		Left l'  -> membershipLoop l' tea
		Right fa -> return (fa, l)


mainLoop alpha (tea,ora) =
	init alpha tea >>= loop
  where
	loop l = do
		(fa,l') <- membershipLoop l tea
		mce <- ora fa
		case mce of
			Just ce -> (extend tea $ counterexample ce l') >>= loop
			Nothing -> return l'


accept :: Ord a => FSA a -> Sq a -> Bool
accept fa sq = estate `elem` (accepting fa) where
	bstate = begin fa
	estate = foldl tr bstate sq
	tr s a = transition fa ! (s,a) 


extend tea' l = do
		extt <- mapM getMs [s ++ e | s <- sa, e <- et]
		return $ L alpha st et (fromList extt)
  where
  	tea = memoized l tea'
	st = start l
	et = end l
	alpha = alphabet l
	sa = nub $ st ++ [s++[a] | s <- st, a <- alpha]
	getMs s = do
		b <- tea s
		return (s,b)

counterexample t l = l { start = st } where
	st = nub $ inits t ++ start l

toDot :: Show a => FSA a -> String
toDot fa = unlines $ "digraph {":(fnodes ++ fedges ++ ["}"]) where
	style = "solid"
	edges = [(a,l,b) | ((a,l),b) <- toList (transition fa)]
	fnodes = map fn (states fa)
	fedges = map fe edges
	guard f kv s = if f s then Just kv else Nothing
	accept = guard (`elem` accepting fa) ("style","filled")
	start  = guard (== begin fa) ("peripheries","2")
	fn s  = show s ++ (fatt $ catMaybes [Just nodeAtt, accept s, start s])
	nodeAtt = ("shape","circle")
	edgeAtts = [("style",style),("labelfloat","true")]
	fatt al = " [" ++ (concat . intersperse  ", " . map eq $ al) ++ "]"
		where eq (a,b) = a ++ "=\"" ++ b ++ "\""
	label l = ("label",show l)
	fe (a,l,b) = show a ++ " -> " ++ show b ++ fatt (label l:edgeAtts)


teacher :: Teacher Char
teacher "00" = return True
teacher "11" = return True
teacher _    = return False

ioracle :: Oracle Char
ioracle fa = do 
	putStrLn "\nNew FSA. Please wait."
	writeFile dotPath (toDot fa)
	runCommand $ "dot -Tpng -o " ++ dotPng ++ " " ++ dotPath ++ "; " ++
		"open " ++ dotPng
	ce <- getLine
	if null ce
		then return Nothing
		else return $ Just ce
  where
  	dotPath = "foo.dot"
  	dotPng = "foo.png"

iteacher :: Teacher Char
iteacher s = do
	putStr $ "\naccept '" ++ s ++"'?"
	loop
  where
  	loop = do
		c <- getChar
		case c of
			'y' -> return True
			'n' -> return False
			_       -> putStrLn "?" >> loop

main :: IO (Learner Char)
main = mainLoop "01" (iteacher,ioracle) 