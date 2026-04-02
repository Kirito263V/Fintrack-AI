import sqlite3
import numpy as np
class target:
    def __init__(self,email):
        self.email = email
        pass

    def monthly_target(self):
        conn = sqlite3.connect("fintrackai.db")
        cur = conn.cursor()
        ami = 0
        mi = 0
        g = 0
        t = 0
        mf = 0
        lep = 0
        r = 0
        b = 0
        f = 0
        en = 0
        ed = 0
        es = 0
        m = 0
        d = 0

        i = mi + ami
        e = g + t + mf + lep + r + b + f + en + ed + es + m
        
        n = i - e

        Fd = 1 - min(0.03 * d, 0.18)
        Nd = n*Fd

        if n/i < 0.15:
            b = 0.3
        elif n/i < 0.3:
            b = 0.2
        else:
            b = 0.1

        S0 = Nd(1-b)

        Ef = lep + r + b + mf + ed

        rf = Ef/i

        if rf >= 0.6:
            Ff = 0.85
        elif rf >= 0.4:
            Ff = 0.92
        else:
            Ff = 1    

        S1 = S0 * Ff
        cur.execute(f'''select created_at, groceries+travel+medfit+LeP+monthly_rent+m_bills+
            fashion+entertainment+education+emsaving+MISCELLANEOUS from expenseprofile
            where user_id = 
            (Select user_id from user where email = {self.email})
            order by created_at asc''')
        x = cur.fetchall()
        monthly_expense = []
        for i in range(len(x)):
            monthly_expense.append(x[i][1])
        
        mn = sum(monthly_expense)/len(x)
        std = np.std(monthly_expense)
        v = std/mn
        fv = max(0.8,1-0.5*v)
        cur.execute('''
            SELECT 
                GOAL_AMOUNT,SAVE_MONTH,
                    CEIL((JULIANDAY(END_DATE)-JULIANDAY(START_DATE))/30.0)
            ''')
        rt = self.goal_tracker()
        c = sum(rt[0])/sum(rt[1])
        


    def goal_tracker(self):
        conn = sqlite3.connect("fintrackai.db")
        cur = conn.cursor()
        cur.execute(f'''
                    SELECT 
                        GOAL_AMOUNT,SAVE_MONTH,
                            CEIL((JULIANDAY(END_DATE)-JULIANDAY(START_DATE))/30.0)
                    FROM GOALS JOIN GOAL_HISTORY USING(GOALID) 
                    WHERE GOALS.USER_ID = (Select user_id from user where email = {self.email})
                    AND GOALID = (Select MAX(GOALID) from  USER JOIN GOALS USING(USER_ID)
                    where email = "yadavbeauty74@gmail.com")
                    ''')
        x = cur.fetchall()
        actualdm = [ i[1] for i in x]
        print(x)
        if len(x)==0:
            return 1
        GA = x[0][0]
        sm = 0
        fixedmn = x[0][-1]
        targetedmn =[] 
        for i  in range(len(x)):
            mntarget = (GA-sm)/(fixedmn-i)
            sm = sm+x[i][1]
            targetedmn.append(mntarget)
        
        return targetedmn,actualdm